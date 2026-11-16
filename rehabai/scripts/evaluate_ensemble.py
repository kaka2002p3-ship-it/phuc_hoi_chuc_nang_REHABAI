"""Strict validation-selected ensemble of RehabMotionNet v2 and CTR-GCN v1."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from shared.metrics import accuracy_score, precision_recall_fscore_support
from training.checkpoint_utils import compute_file_sha256, load_checkpoint_strict
from training.datasets.rehab_dataset import RehabDataset
from training.model_registry import get_model

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
DATA = ROOT / "data/stage3_upper_limb/processed/keypoints"
CLASS_MAPPING = {0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"}

V2_CONFIG = {"use_hand": True, "use_kinematic": True, "use_contrastive": True, "use_mstcn": True, "use_attention": True, "upper_limb_only": True}
CTR_CONFIG = {"use_hand": True, "use_kinematic": True, "upper_limb_only": True}


def load_fold_model(model_id, config, signature, ckpt, metadata, norm, fold):
    model = get_model(model_id, config=config)
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    norm_data = json.loads(norm.read_text(encoding="utf-8"))
    hashes = {k: meta[k] for k in ("canonical_provenance_manifest_hash", "canonical_train_manifest_hash")}
    hashes.update({"canonical_val_manifest_hash": meta["canonical_val_manifest_hash"], "canonical_test_manifest_hash": meta["canonical_test_manifest_hash"]})
    load_checkpoint_strict(
        filepath=str(ckpt), model=model, expected_model_id=model_id,
        expected_fold_id=fold, expected_protocol="1.1",
        expected_provenance_hash=hashes["canonical_provenance_manifest_hash"],
        expected_train_manifest_hash=hashes["canonical_train_manifest_hash"],
        expected_normalization_hash=compute_file_sha256(str(norm)),
        expected_class_mapping=CLASS_MAPPING, expected_model_config=config,
        expected_architecture_signature=signature, expected_role="supervised_model", device="cpu",
    )
    return model


@torch.no_grad()
def logits(model, dataset, device):
    model.eval().to(device)
    out, ys = [], []
    for batch in DataLoader(dataset, batch_size=32, shuffle=False):
        result = model(batch["features"].to(device))
        out.append(result[0].detach().cpu())
        ys.append(batch["exercise"].cpu())
    return torch.cat(out), torch.cat(ys)


def macro_f1(y, pred):
    return float(precision_recall_fscore_support(y, pred, average="macro", zero_division=0, labels=list(CLASS_MAPPING))[2])


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = []
    for i in range(1, 11):
        fold = f"fold_{i:02d}"
        fold_dir = ROOT / f"data/stage3_upper_limb/loso/{fold}"
        norm = fold_dir / "normalization.json"
        metadata = fold_dir / "metadata.json"
        v2 = load_fold_model("RehabMotionNet", V2_CONFIG, "rehab_motionnet_upper_limb_v2", ROOT / f"experiments/upper_limb_v1/training/checkpoints/{fold}/RehabMotionNet_{fold}_supervised_model.pth", metadata, norm, fold)
        ctr = load_fold_model("UpperLimbCTRGCN", CTR_CONFIG, "upper_limb_ctr_gcn_v1", ROOT / f"experiments/ctr_gcn_v1/checkpoints/{fold}/UpperLimbCTRGCN_{fold}_supervised_model.pth", metadata, norm, fold)
        train = RehabDataset(str(DATA), str(SOURCE), str(fold_dir / "train_manifest.csv"), "train", str(norm), fold, False)
        val = RehabDataset(str(DATA), str(SOURCE), str(fold_dir / "val_manifest.csv"), "val", str(norm), fold, False)
        test = RehabDataset(str(DATA), str(SOURCE), str(fold_dir / "test_manifest.csv"), "test", str(norm), fold, False)
        v2_val, y_val = logits(v2, val, device); ctr_val, _ = logits(ctr, val, device)
        best_alpha, best_score = 0.0, -1.0
        for j in range(0, 21):
            alpha = j / 20.0
            score = macro_f1(y_val, torch.argmax(alpha * v2_val + (1 - alpha) * ctr_val, dim=1))
            if score > best_score:
                best_alpha, best_score = alpha, score
        v2_test, y_test = logits(v2, test, device); ctr_test, _ = logits(ctr, test, device)
        pred = torch.argmax(best_alpha * v2_test + (1 - best_alpha) * ctr_test, dim=1)
        rows.append({"fold_id": fold, "alpha_v2": best_alpha, "validation_f1": best_score, "test_f1_macro": macro_f1(y_test, pred), "test_accuracy": float(accuracy_score(y_test, pred)), "sample_count": len(test)})
        print(f"{fold}: alpha_v2={best_alpha:.2f}, val_f1={best_score:.4f}, test_f1={rows[-1]['test_f1_macro']:.4f}")
    result = {"protocol": "strict subject-wise 10-fold LOSO; alpha selected on validation only", "folds": rows, "mean_test_f1_macro": statistics.mean([r["test_f1_macro"] for r in rows]), "std_test_f1_macro": statistics.stdev([r["test_f1_macro"] for r in rows]), "mean_test_accuracy": statistics.mean([r["test_accuracy"] for r in rows]), "mean_alpha_v2": statistics.mean([r["alpha_v2"] for r in rows])}
    out = ROOT / "reports/evaluation/loso_ensemble_v1.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
