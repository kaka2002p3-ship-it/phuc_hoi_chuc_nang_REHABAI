"""Equal-probability ensemble of existing Optimized-v1 LOSO checkpoints.

No fitting or test-fold weight selection is performed. Each fold averages the
softmax probabilities from the predeclared seeds 42, 7 and 2026. Checkpoints
are loaded through the strict fold/provenance contract before inference.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from shared.metrics import accuracy_score, precision_recall_fscore_support
from training.checkpoint_utils import compute_file_sha256, load_checkpoint_strict
from training.datasets.rehab_dataset import RehabDataset
from training.model_registry import get_model


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
DATA = ROOT / "data/stage3_upper_limb/processed/keypoints"
REPORTS = ROOT / "reports/evaluation"
SEEDS = (42, 7, 2026)
MODEL_CONFIG = {
    "use_hand": True,
    "use_kinematic": True,
    "use_contrastive": False,
    "use_mstcn": True,
    "use_attention": False,
    "upper_limb_only": True,
}
CLASS_MAPPING = {0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"}


def checkpoint(seed: int, fold: str) -> Path:
    if seed == 42:
        base = ROOT / "experiments/optimized_v1/checkpoints"
    else:
        base = ROOT / f"experiments/multiseed_confirmation/optimized_v1_seed_{seed}/checkpoints"
    return base / fold / f"RehabMotionNet_{fold}_supervised_model.pth"


def load_model(seed: int, fold: str, fold_dir: Path):
    metadata = json.loads((fold_dir / "metadata.json").read_text(encoding="utf-8"))
    path = checkpoint(seed, fold)
    model = get_model("RehabMotionNet", config=MODEL_CONFIG)
    loaded = load_checkpoint_strict(
        filepath=str(path), model=model, expected_model_id="RehabMotionNet",
        expected_fold_id=fold, expected_protocol="1.1",
        expected_provenance_hash=metadata["canonical_provenance_manifest_hash"],
        expected_train_manifest_hash=metadata["canonical_train_manifest_hash"],
        expected_normalization_hash=compute_file_sha256(str(fold_dir / "normalization.json")),
        expected_class_mapping=CLASS_MAPPING, expected_model_config=MODEL_CONFIG,
        expected_architecture_signature="rehab_motionnet_upper_limb_v2",
        expected_role="supervised_model", device="cpu",
    )
    actual_seed = loaded["metadata"].get("training_inputs", {}).get("seed")
    if actual_seed != seed:
        raise ValueError(f"Checkpoint seed mismatch for {fold}: expected {seed}, got {actual_seed}")
    return model, compute_file_sha256(str(path))


@torch.no_grad()
def infer(model, loader, device):
    model.eval().to(device)
    exercise, completion, targets, completion_targets = [], [], [], []
    for batch in loader:
        out_ex, out_comp = model(batch["features"].to(device))
        exercise.append(torch.softmax(out_ex.float(), dim=1).cpu())
        completion.append(torch.sigmoid(out_comp.float()).reshape(-1).cpu())
        targets.append(batch["exercise"].cpu())
        completion_targets.append(batch["completion"].reshape(-1).long().cpu())
    return map(torch.cat, (exercise, completion, targets, completion_targets))


def classification_metrics(target, prediction, labels):
    precision, recall, f1, support = precision_recall_fscore_support(
        target, prediction, average=None, zero_division=0, labels=labels
    )
    macro = precision_recall_fscore_support(
        target, prediction, average="macro", zero_division=0, labels=labels
    )
    return {
        "accuracy": float(accuracy_score(target, prediction)),
        "precision_macro": float(macro[0]),
        "recall_macro": float(macro[1]),
        "f1_macro": float(macro[2]),
        "per_class": {
            str(label): {"precision": float(precision[i]), "recall": float(recall[i]),
                         "f1": float(f1[i]), "support": int(support[i])}
            for i, label in enumerate(labels)
        },
    }


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = []
    for index in range(1, 11):
        fold = f"fold_{index:02d}"
        fold_dir = ROOT / "data/stage3_upper_limb/loso" / fold
        dataset = RehabDataset(
            str(DATA), str(SOURCE), str(fold_dir / "test_manifest.csv"), "test",
            str(fold_dir / "normalization.json"), fold, False,
        )
        loader = DataLoader(dataset, batch_size=32, shuffle=False)
        probabilities, completion_probabilities, hashes = [], [], {}
        expected_targets = expected_completion = None
        for seed in SEEDS:
            model, artifact_hash = load_model(seed, fold, fold_dir)
            probs, comp_probs, targets, comp_targets = infer(model, loader, device)
            if expected_targets is not None and (
                not torch.equal(targets, expected_targets)
                or not torch.equal(comp_targets, expected_completion)
            ):
                raise ValueError(f"Inference order changed within {fold}")
            expected_targets, expected_completion = targets, comp_targets
            probabilities.append(probs)
            completion_probabilities.append(comp_probs)
            hashes[str(seed)] = artifact_hash
            del model
        prediction = torch.stack(probabilities).mean(0).argmax(1)
        completion_prediction = (torch.stack(completion_probabilities).mean(0) >= 0.5).long()
        exercise_metrics = classification_metrics(expected_targets, prediction, list(CLASS_MAPPING))
        completion_metrics = classification_metrics(expected_completion, completion_prediction, [0, 1])
        rows.append({
            "fold_id": fold,
            "model_name": "OptimizedV1MultiSeedEnsemble",
            **exercise_metrics,
            "completion_accuracy": completion_metrics["accuracy"],
            "completion_precision_macro": completion_metrics["precision_macro"],
            "completion_recall_macro": completion_metrics["recall_macro"],
            "completion_f1_macro": completion_metrics["f1_macro"],
            "sample_count": len(dataset),
            "observed_classes": sorted({int(value) for value in expected_targets.tolist()}),
            "class_coverage_complete": set(expected_targets.tolist()) == set(CLASS_MAPPING),
            "ensemble": {"seeds": list(SEEDS), "method": "equal_softmax_probability_mean", "checkpoint_sha256": hashes},
        })
        print(f"{fold}: f1={exercise_metrics['f1_macro']:.4f} acc={exercise_metrics['accuracy']:.4f}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    output = REPORTS / "loso_optimized_v1_multiseed_ensemble.json"
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "mean_f1_macro": statistics.mean(row["f1_macro"] for row in rows),
        "mean_accuracy": statistics.mean(row["accuracy"] for row in rows),
        "mean_completion_f1_macro": statistics.mean(row["completion_f1_macro"] for row in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
