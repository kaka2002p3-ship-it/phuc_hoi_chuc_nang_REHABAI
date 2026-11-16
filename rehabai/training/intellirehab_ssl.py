"""Subject-disjoint self-supervised pretraining for IntelliRehabDS."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from shared.preprocessing.sequence import resample_sequence
from training.device import select_training_device
from training.models.shared_encoder import SharedMotionEncoder


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_view(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    view = x.copy()
    crop = int(rng.integers(76, 97))
    start = int(rng.integers(0, len(view) - crop + 1))
    view = resample_sequence(view[start : start + crop], 96).astype(np.float32)
    present = view != 0
    noise = rng.normal(0.0, 0.008, size=view.shape).astype(np.float32)
    view[present] += noise[present]
    # Mask whole time spans and common pose joints; zeros remain genuine
    # missing cross-domain channels rather than synthetic landmarks.
    if rng.random() < 0.6:
        width = int(rng.integers(3, 13))
        offset = int(rng.integers(0, 97 - width))
        view[offset : offset + width] = 0
    for joint in (11, 12, 13, 14, 15, 16, 23, 24):
        if rng.random() < 0.08:
            view[:, joint * 3 : joint * 3 + 3] = 0
    return view


class ContrastiveSkeletonDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, train: bool, seed: int):
        self.rows = frame.to_dict("records")
        self.train = train
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        """Select a reproducible augmentation stream for one training epoch."""
        self.epoch = int(epoch)

    def _rng(self, row: dict, index: int, view: int) -> np.random.Generator:
        material = f"{self.seed}:{self.epoch}:{index}:{row['sample_id']}:{view}"
        stable_seed = int(hashlib.sha256(material.encode()).hexdigest()[:16], 16)
        return np.random.default_rng(stable_seed)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with np.load(row["ssl_feature_path"], allow_pickle=False) as payload:
            x = np.asarray(payload["features"], dtype=np.float32)
        if x.shape != (96, 237) or not np.isfinite(x).all():
            raise ValueError(f"Invalid SSL feature: {row['ssl_feature_path']}")
        if self.train:
            rng1, rng2 = self._rng(row, index, 0), self._rng(row, index, 1)
        else:
            stable = int(hashlib.sha256(row["sample_id"].encode()).hexdigest()[:8], 16)
            rng1 = np.random.default_rng(self.seed + stable)
            rng2 = np.random.default_rng(self.seed + stable + 1)
        return torch.from_numpy(make_view(x, rng1)), torch.from_numpy(make_view(x, rng2))


class ContrastiveModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = SharedMotionEncoder()
        self.projector = nn.Sequential(nn.Linear(128, 128), nn.GELU(), nn.Linear(128, 64))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.projector(self.encoder(x)), dim=1)


def nt_xent(a: torch.Tensor, b: torch.Tensor, temperature: float) -> torch.Tensor:
    batch = a.shape[0]
    z = torch.cat([a, b], dim=0)
    similarity = z @ z.T / temperature
    similarity.fill_diagonal_(float("-inf"))
    targets = torch.cat([
        torch.arange(batch, 2 * batch, device=z.device),
        torch.arange(0, batch, device=z.device),
    ])
    return F.cross_entropy(similarity, targets)


def validate_ssl_artifact(path: Path, manifest: Path, source_fold: int) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = torch.load(path, map_location="cpu", weights_only=True)
    metadata = payload.get("metadata", {})
    expected = {
        "architecture_signature": "intellirehab_ssl_encoder_v1",
        "input_contract": "common_upper_limb_237_v1",
        "manifest_sha256": file_sha256(manifest),
        "source_datasets": ["IntelliRehabDS"],
        "ontology_mapping_to_product": None,
        "source_fold": source_fold,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"SSL artifact metadata mismatch for {key}")
    encoder = SharedMotionEncoder()
    encoder.load_state_dict(payload["model_state_dict"], strict=True)
    train_subjects = set(metadata.get("training_subjects", []))
    validation_subjects = set(metadata.get("validation_subjects", []))
    if not train_subjects or not validation_subjects or train_subjects & validation_subjects:
        raise ValueError("SSL artifact has an invalid subject-disjoint split")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-fold", type=int, choices=range(5), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--temperature", type=float, default=0.15)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        validate_ssl_artifact(args.output, args.manifest, args.source_fold)
        print(f"valid={args.output}")
        return
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False
    frame = pd.read_csv(args.manifest, dtype={"subject_id": str}).fillna("")
    required = {"ssl_feature_path", "ssl_feature_status", "source_fold", "product_split"}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError(f"SSL manifest missing columns: {sorted(required - set(frame.columns))}")
    if frame["ssl_feature_status"].ne("ready").any() or frame["product_split"].ne("NOT_ADMITTED").any():
        raise ValueError("Only ready, product-isolated source samples are allowed")
    train_frame = frame[frame.source_fold != args.source_fold].copy()
    val_frame = frame[frame.source_fold == args.source_fold].copy()
    if set(train_frame.subject_id) & set(val_frame.subject_id):
        raise ValueError("Source-subject leakage detected")
    device = select_training_device()
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(ContrastiveSkeletonDataset(train_frame, True, args.seed), batch_size=args.batch_size, shuffle=True, generator=generator, num_workers=0, drop_last=True)
    val_loader = DataLoader(ContrastiveSkeletonDataset(val_frame, False, args.seed), batch_size=args.batch_size, shuffle=False, num_workers=0, drop_last=False)
    model = ContrastiveModel().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    best, best_epoch, stale, best_state = float("inf"), 0, 0, None
    history = []
    for epoch in range(1, args.epochs + 1):
        train_loader.dataset.set_epoch(epoch)
        model.train(); total = 0.0
        for a, b in train_loader:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                loss = nt_xent(model(a.to(device)), model(b.to(device)), args.temperature)
            scaler.scale(loss).backward(); scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer); scaler.update(); total += loss.item()
        train_loss = total / max(1, len(train_loader))
        model.eval(); total = 0.0
        with torch.no_grad():
            for a, b in val_loader:
                total += nt_xent(model(a.to(device)), model(b.to(device)), args.temperature).item()
        val_loss = total / max(1, len(val_loader))
        improved = val_loss < best - 1e-6
        if improved:
            best, best_epoch, stale = val_loss, epoch, 0
            best_state = {key: value.detach().cpu().clone() for key, value in model.encoder.state_dict().items()}
        else:
            stale += 1
        history.append({"epoch": epoch, "train_loss": train_loss, "validation_loss": val_loss, "selected": improved})
        print(f"fold={args.source_fold} epoch={epoch} train={train_loss:.5f} val={val_loss:.5f} best={best_epoch}", flush=True)
        if stale >= args.patience:
            break
    if best_state is None:
        raise RuntimeError("No SSL encoder checkpoint selected")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "architecture_signature": "intellirehab_ssl_encoder_v1",
        "input_contract": "common_upper_limb_237_v1",
        "manifest_sha256": file_sha256(args.manifest),
        "source_datasets": ["IntelliRehabDS"],
        "ontology_mapping_to_product": None,
        "objective": "temporal_view_nt_xent",
        "source_fold": args.source_fold,
        "training_subjects": sorted(set(train_frame.subject_id)),
        "validation_subjects": sorted(set(val_frame.subject_id)),
        "best_epoch": best_epoch,
        "seed": args.seed,
    }
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    torch.save({"model_state_dict": best_state, "metadata": metadata}, temporary)
    os.replace(temporary, args.output)
    args.output.with_suffix(".summary.json").write_text(json.dumps({**metadata, "best_validation_loss": best, "history": history}, indent=2), encoding="utf-8")
    print(f"saved={args.output}")


if __name__ == "__main__":
    main()
