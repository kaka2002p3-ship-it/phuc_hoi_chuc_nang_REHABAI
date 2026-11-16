"""Multi-source auxiliary pretraining without cross-dataset label coercion."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from shared.preprocessing.kinematics import get_kinematic_features
from shared.preprocessing.normalization import normalize_landmarks
from shared.preprocessing.sequence import resample_sequence
from training.device import select_training_device
from training.models.shared_encoder import SharedMotionEncoder

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


class ExternalMotionDataset(Dataset):
    def __init__(self, manifest: Path):
        frame = pd.read_csv(manifest).fillna("")
        frame = frame[frame.feature_status == "ready"].copy()
        if frame.empty:
            raise ValueError("No ready external features; run extraction first")
        self.frame = frame.reset_index(drop=True)
        self.rows = self.frame.to_dict("records")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with np.load(row["feature_path"], allow_pickle=False) as data:
            pose = np.asarray(data["pose_landmarks"], np.float32)
            lh = np.asarray(data["left_hand_landmarks"], np.float32) if "left_hand_landmarks" in data else np.zeros((len(pose), 21, 3), np.float32)
            rh = np.asarray(data["right_hand_landmarks"], np.float32) if "right_hand_landmarks" in data else np.zeros((len(pose), 21, 3), np.float32)
        # Normalize MediaPipe data here; REHAB24 has already been normalized.
        # Missing landmarks are encoded as all-zero triples and must remain
        # zero. Translating those triples would otherwise create synthetic
        # joints at -body_center / shoulder_width.
        if row["dataset"] == "MobiPhysio":
            pose_missing = ~np.any(pose, axis=2)
            left_missing = ~np.any(lh, axis=2)
            right_missing = ~np.any(rh, axis=2)
            pose, lh, rh = normalize_landmarks(pose, lh, rh)
            pose[pose_missing] = 0.0
            lh[left_missing] = 0.0
            rh[right_missing] = 0.0
        else:
            # REHAB24-6 exposes only bilateral shoulder/elbow/wrist tracks.
            # Old converted artifacts may contain translated values at the
            # other MediaPipe indices, so enforce the released-joint mask at
            # load time as part of the external feature contract.
            available = np.zeros(33, dtype=bool)
            available[[11, 12, 13, 14, 15, 16]] = True
            pose[:, ~available, :] = 0.0
        kin = get_kinematic_features(pose, fps=30.0)
        if row["dataset"] == "REHAB24-6":
            # Hip-dependent shoulder/trunk angles do not exist in REHAB24-6.
            # Keep only elbow angles, their velocities and wrist velocities.
            kin[:, [0, 1, 4, 5, 6, 9]] = 0.0
        pose = resample_sequence(pose, 96); lh = resample_sequence(lh, 96); rh = resample_sequence(rh, 96); kin = resample_sequence(kin, 96)
        # Per-sequence scaling avoids leaking target fold normalization into external pretraining.
        mean, std = kin.mean(0, keepdims=True), kin.std(0, keepdims=True)
        kin = (kin - mean) / np.maximum(std, 1e-5)
        features = np.concatenate([pose.reshape(96, 99), lh.reshape(96, 63), rh.reshape(96, 63), kin], axis=1)
        dataset_id = 0 if row["dataset"] == "REHAB24-6" else 1
        exercise = int(row["source_exercise_id"]) - 1
        correctness = float(row["correctness"]) if row["correctness"] != "" else -1.0
        quality = float(row["quality_score"]) / 100.0 if row["quality_score"] != "" else -1.0
        return torch.tensor(features, dtype=torch.float32), dataset_id, exercise, correctness, quality


class MultiSourcePretrainer(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = SharedMotionEncoder()
        self.r24_exercise = nn.Linear(128, 6)
        self.mobi_exercise = nn.Linear(128, 6)
        self.correctness = nn.Linear(128, 1)
        self.quality = nn.Linear(128, 1)

    def forward(self, x):
        z = self.encoder(x)
        return z, self.r24_exercise(z), self.mobi_exercise(z), self.correctness(z).squeeze(1), self.quality(z).squeeze(1)


def subjectwise_split(dataset: ExternalMotionDataset, validation_fraction: float, seed: int):
    """Split each source by subject so validation never sees a training person."""
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between zero and one")
    validation_subjects: dict[str, list[str]] = {}
    for source_index, source in enumerate(sorted(dataset.frame["dataset"].unique())):
        subjects = sorted(dataset.frame.loc[dataset.frame["dataset"] == source, "subject_id"].unique())
        if len(subjects) < 2:
            raise ValueError(f"External source {source} needs at least two ready subjects")
        rng = random.Random(seed + 1009 * source_index)
        rng.shuffle(subjects)
        count = min(len(subjects) - 1, max(1, round(len(subjects) * validation_fraction)))
        validation_subjects[source] = sorted(subjects[:count])

    is_validation = np.zeros(len(dataset), dtype=bool)
    for source, subjects in validation_subjects.items():
        is_validation |= (
            dataset.frame["dataset"].eq(source)
            & dataset.frame["subject_id"].isin(subjects)
        ).to_numpy()
    train_indices = np.flatnonzero(~is_validation).tolist()
    validation_indices = np.flatnonzero(is_validation).tolist()
    if not train_indices or not validation_indices:
        raise ValueError("Subject-wise external split produced an empty partition")
    return train_indices, validation_indices, validation_subjects


def pretraining_loss(outputs, source, exercise, correctness, quality, ce, bce, mse):
    _, r24, mobi, corr, score = outputs
    loss = torch.zeros((), device=source.device)
    mr = source == 0
    mm = source == 1
    if mr.any():
        loss = loss + ce(r24[mr], exercise[mr])
    if mm.any():
        loss = loss + ce(mobi[mm], exercise[mm])
    mc = correctness >= 0
    mq = quality >= 0
    if mc.any():
        loss = loss + 0.5 * bce(corr[mc], correctness[mc])
    if mq.any():
        loss = loss + 0.5 * mse(torch.sigmoid(score[mq]), quality[mq])
    return loss


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/external_pretraining_v1/external_manifest.csv")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/external_pretraining_v1/external_encoder.pth")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--patience", type=int, default=8)
    args = parser.parse_args()
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    device = select_training_device()
    dataset = ExternalMotionDataset(args.manifest)
    source_datasets = sorted(str(value) for value in dataset.frame["dataset"].unique())
    train_indices, validation_indices, validation_subjects = subjectwise_split(
        dataset, args.validation_fraction, args.seed
    )
    # MobiPhysio has more videos than REHAB24-6. Balance source domains per
    # epoch so the shared encoder is not dominated by the larger corpus.
    train_frame = dataset.frame.iloc[train_indices]
    source_counts = train_frame["dataset"].value_counts().to_dict()
    sample_weights = [
        1.0 / float(source_counts[dataset.frame.iloc[index]["dataset"]])
        for index in train_indices
    ]
    train_sampler = WeightedRandomSampler(
        weights=torch.tensor(sample_weights, dtype=torch.double),
        num_samples=len(train_indices),
        replacement=True,
        generator=torch.Generator().manual_seed(args.seed),
    )
    train_loader = DataLoader(
        torch.utils.data.Subset(dataset, train_indices),
        batch_size=args.batch_size,
        sampler=train_sampler,
        num_workers=0,
    )
    validation_loader = DataLoader(
        torch.utils.data.Subset(dataset, validation_indices),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )
    model = MultiSourcePretrainer().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    ce, bce, mse = nn.CrossEntropyLoss(), nn.BCEWithLogitsLoss(), nn.SmoothL1Loss()
    history = []
    best_epoch, best_validation_loss, stale_epochs = 0, float("inf"), 0
    best_encoder_state = None
    for epoch in range(args.epochs):
        model.train(); total = 0.0
        for x, source, exercise, correctness, quality in train_loader:
            x=x.to(device); source=source.to(device); exercise=exercise.to(device); correctness=correctness.to(device); quality=quality.to(device)
            loss = pretraining_loss(model(x), source, exercise, correctness, quality, ce, bce, mse)
            opt.zero_grad(set_to_none=True); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); total += loss.item()
        train_loss = total / max(1, len(train_loader))

        model.eval(); validation_total = 0.0
        with torch.no_grad():
            for x, source, exercise, correctness, quality in validation_loader:
                x=x.to(device); source=source.to(device); exercise=exercise.to(device); correctness=correctness.to(device); quality=quality.to(device)
                validation_total += pretraining_loss(
                    model(x), source, exercise, correctness, quality, ce, bce, mse
                ).item()
        validation_loss = validation_total / max(1, len(validation_loader))
        improved = validation_loss < best_validation_loss - 1e-6
        if improved:
            best_epoch = epoch + 1
            best_validation_loss = validation_loss
            stale_epochs = 0
            # Keep the selected artifact device-independent and release GPU
            # references before the next epoch/checkpoint selection.
            best_encoder_state = {
                key: value.detach().cpu().clone()
                for key, value in model.encoder.state_dict().items()
            }
        else:
            stale_epochs += 1
        history.append({
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "validation_loss": validation_loss,
            "selected": improved,
        })
        print(
            f"epoch={epoch+1} train_loss={train_loss:.5f} "
            f"validation_loss={validation_loss:.5f} best_epoch={best_epoch}",
            flush=True,
        )
        if stale_epochs >= args.patience:
            print(f"early_stopping patience={args.patience}", flush=True)
            break
    if best_encoder_state is None:
        raise RuntimeError("External pretraining did not produce a selectable encoder")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest_hash = file_sha256(args.manifest)
    metadata = {
        "architecture_signature": "external_multisource_encoder_v1",
        "manifest_sha256": manifest_hash,
        "source_datasets": source_datasets,
        "ontology_mapping_to_product": None,
        "sample_count": len(dataset),
        "training_sample_count": len(train_indices),
        "validation_sample_count": len(validation_indices),
        "validation_subjects": validation_subjects,
        "source_sampling": "inverse_source_frequency_with_replacement",
        "source_training_counts": {str(key): int(value) for key, value in source_counts.items()},
        "selection_metric": "subject_disjoint_validation_loss",
        "best_epoch": best_epoch,
        "seed": args.seed,
    }
    torch.save({"model_state_dict": best_encoder_state, "metadata": metadata}, args.output)
    summary = {
        **metadata,
        "best_validation_loss": best_validation_loss,
        "history": history,
    }
    (args.output.parent / "training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"saved={args.output}")


if __name__ == "__main__":
    main()
