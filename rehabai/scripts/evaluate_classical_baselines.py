"""Evaluate fixed Majority and Random-Forest baselines under strict data-01 LOSO.

The feature extractor and hyperparameters are declared once and shared by all
folds. Test folds are never used for fitting, feature selection, or tuning.
"""
from __future__ import annotations

import json
import os
import platform
import statistics
from pathlib import Path
from typing import Iterable

import numpy as np

from shared.metrics import accuracy_score, precision_recall_fscore_support
from training.datasets.rehab_dataset import RehabDataset

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/stage3_upper_limb/processed/keypoints"
SOURCE_DIR = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
LOSO_DIR = ROOT / "data/stage3_upper_limb/loso"
REPORT_DIR = ROOT / "reports/evaluation"
SEED = 42
EXERCISE_LABELS = [0, 1, 2, 3]
COMPLETION_LABELS = [0, 1]


def _summary_kinematics(features: np.ndarray) -> np.ndarray:
    """Return a fixed 48-D mean/std/min/max summary of 12 kinematic channels."""
    if features.shape != (96, 237):
        raise ValueError(f"Expected (96, 237), got {features.shape}")
    kinematics = features[:, 225:237]
    return np.concatenate(
        [
            np.mean(kinematics, axis=0),
            np.std(kinematics, axis=0),
            np.min(kinematics, axis=0),
            np.max(kinematics, axis=0),
        ]
    ).astype(np.float32)


def _load(dataset: RehabDataset) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features, exercises, completions = [], [], []
    for index in range(len(dataset)):
        row = dataset[index]
        features.append(_summary_kinematics(row["features"].numpy()))
        exercises.append(int(row["exercise"].item()))
        completions.append(int(row["completion"].item()))
    return (
        np.stack(features),
        np.asarray(exercises, dtype=np.int64),
        np.asarray(completions, dtype=np.int64),
    )


def _majority(values: np.ndarray) -> int:
    unique, counts = np.unique(values, return_counts=True)
    return int(unique[np.argmax(counts)])


def _fit_linear_svm(x: np.ndarray, y: np.ndarray, num_classes: int,
                    epochs: int = 1200, learning_rate: float = 0.03,
                    reg_strength: float = 1e-3):
    """Deterministic full-batch multiclass hinge-loss classifier (NumPy-only)."""
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-6] = 1.0
    z = np.concatenate([((x - mean) / scale).astype(np.float64), np.ones((len(x), 1))], axis=1)
    weights = np.zeros((z.shape[1], num_classes), dtype=np.float64)
    counts = np.bincount(y, minlength=num_classes).astype(np.float64)
    class_weight = counts.sum() / np.maximum(counts * num_classes, 1.0)
    for epoch in range(epochs):
        scores = z @ weights
        margins = scores - scores[np.arange(len(y)), y][:, None] + 1.0
        margins[np.arange(len(y)), y] = 0.0
        wrong = np.argmax(margins, axis=1)
        active = margins[np.arange(len(y)), wrong] > 0.0
        grad = reg_strength * weights
        for row in np.flatnonzero(active):
            w = class_weight[y[row]] / len(y)
            grad[:, wrong[row]] += w * z[row]
            grad[:, y[row]] -= w * z[row]
        weights -= (learning_rate / (1.0 + 0.002 * epoch)) * grad
    return weights, mean, scale


def _predict_linear_svm(x: np.ndarray, model) -> np.ndarray:
    weights, mean, scale = model
    z = np.concatenate([((x - mean) / scale).astype(np.float64), np.ones((len(x), 1))], axis=1)
    return np.argmax(z @ weights, axis=1).astype(np.int64)


def _task_metrics(targets: Iterable[int], predictions: Iterable[int], labels: list[int]) -> dict:
    targets = np.asarray(list(targets), dtype=np.int64)
    predictions = np.asarray(list(predictions), dtype=np.int64)
    precision, recall, f1, support = precision_recall_fscore_support(
        targets, predictions, average=None, zero_division=0, labels=labels
    )
    support_total = int(np.sum(support))
    confusion = [
        [int(np.sum((targets == actual) & (predictions == predicted))) for predicted in labels]
        for actual in labels
    ]
    return {
        "accuracy": accuracy_score(targets, predictions),
        "precision_macro": float(np.mean(precision)),
        "recall_macro": float(np.mean(recall)),
        "f1_macro": float(np.mean(f1)),
        "f1_weighted": float(np.sum(f1 * support) / support_total) if support_total else 0.0,
        "per_class": {
            str(label): {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(labels)
        },
        "confusion_matrix": confusion,
        "sample_count": int(len(targets)),
        "observed_classes": sorted({int(value) for value in targets}),
    }


def _fold_result(
    fold_id: str,
    model_name: str,
    exercise_targets: np.ndarray,
    exercise_predictions: np.ndarray,
    completion_targets: np.ndarray,
    completion_predictions: np.ndarray,
    metadata: dict,
    model_details: dict,
) -> dict:
    exercise = _task_metrics(exercise_targets, exercise_predictions, EXERCISE_LABELS)
    completion = _task_metrics(completion_targets, completion_predictions, COMPLETION_LABELS)
    return {
        "fold_id": fold_id,
        "model_name": model_name,
        **exercise,
        "class_coverage_complete": set(exercise_targets) == set(EXERCISE_LABELS),
        "completion_accuracy": completion["accuracy"],
        "completion_precision_macro": completion["precision_macro"],
        "completion_recall_macro": completion["recall_macro"],
        "completion_f1_macro": completion["f1_macro"],
        "completion_f1_weighted": completion["f1_weighted"],
        "completion_per_class": completion["per_class"],
        "completion_confusion_matrix": completion["confusion_matrix"],
        "completion_sample_count": completion["sample_count"],
        "completion_observed_classes": completion["observed_classes"],
        "metadata": {
            "protocol_version": metadata["protocol_version"],
            "seed": SEED,
            "test_subject": metadata["test_subject"],
            "validation_subjects": metadata["validation_subjects"],
            "train_subjects": metadata["train_subjects"],
            "canonical_train_manifest_hash": metadata["canonical_train_manifest_hash"],
            "canonical_test_manifest_hash": metadata["canonical_test_manifest_hash"],
            "normalization_scope": "fold_train_only",
            "augmentation": False,
            "feature_contract": "48-D mean/std/min/max of fold-normalized 12-D kinematics",
            "test_set_tuning": False,
            "model_details": model_details,
        },
    }


def _metric(rows: list[dict], key: str) -> dict:
    values = [float(row[key]) for row in rows]
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    if not os.environ.get("REHABAI_PROVENANCE_HMAC_KEY"):
        raise RuntimeError("REHABAI_PROVENANCE_HMAC_KEY is required for strict loading")
    majority_rows: list[dict] = []
    svm_rows: list[dict] = []
    svm_config = {
        "solver": "full_batch_multiclass_hinge_numpy",
        "epochs": 1200,
        "learning_rate": 0.03,
        "reg_strength": 1e-3,
        "seed": SEED,
    }

    for fold_number in range(1, 11):
        fold_id = f"fold_{fold_number:02d}"
        fold_dir = LOSO_DIR / fold_id
        metadata = json.loads((fold_dir / "metadata.json").read_text(encoding="utf-8"))
        train_dataset = RehabDataset(
            data_dir=str(DATA_DIR), source_dir=str(SOURCE_DIR),
            split_manifest_csv=str(fold_dir / "train_manifest.csv"), split="train",
            normalization_json=str(fold_dir / "normalization.json"), fold_id=fold_id,
            apply_augmentation=False,
        )
        test_dataset = RehabDataset(
            data_dir=str(DATA_DIR), source_dir=str(SOURCE_DIR),
            split_manifest_csv=str(fold_dir / "test_manifest.csv"), split="test",
            normalization_json=str(fold_dir / "normalization.json"), fold_id=fold_id,
            apply_augmentation=False,
        )
        train_x, train_exercise, train_completion = _load(train_dataset)
        test_x, test_exercise, test_completion = _load(test_dataset)

        majority_exercise = np.full_like(test_exercise, _majority(train_exercise))
        majority_completion = np.full_like(test_completion, _majority(train_completion))
        majority_rows.append(_fold_result(
            fold_id, "MajorityClass", test_exercise, majority_exercise,
            test_completion, majority_completion, metadata,
            {"fit_scope": "training labels only", "tie_break": "lowest class index"},
        ))

        exercise_svm = _fit_linear_svm(train_x, train_exercise, 4, svm_config["epochs"], svm_config["learning_rate"], svm_config["reg_strength"])
        completion_svm = _fit_linear_svm(train_x, train_completion, 2, svm_config["epochs"], svm_config["learning_rate"], svm_config["reg_strength"])
        svm_rows.append(_fold_result(
            fold_id, "LinearSVMKinematics", test_exercise, _predict_linear_svm(test_x, exercise_svm),
            test_completion, _predict_linear_svm(test_x, completion_svm), metadata,
            svm_config,
        ))
        print(f"{fold_id}: majority_f1={majority_rows[-1]['f1_macro']:.4f} "
              f"svm_f1={svm_rows[-1]['f1_macro']:.4f}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "loso_majority.json").write_text(json.dumps(majority_rows, indent=2), encoding="utf-8")
    (REPORT_DIR / "loso_linear_svm.json").write_text(json.dumps(svm_rows, indent=2), encoding="utf-8")
    models = {
        "majority": {
            "exercise_macro_f1": _metric(majority_rows, "f1_macro"),
            "accuracy": _metric(majority_rows, "accuracy"),
            "completion_macro_f1": _metric(majority_rows, "completion_f1_macro"),
            "completion_accuracy": _metric(majority_rows, "completion_accuracy"),
        },
        "linear_svm": {
            "exercise_macro_f1": _metric(svm_rows, "f1_macro"),
            "accuracy": _metric(svm_rows, "accuracy"),
            "completion_macro_f1": _metric(svm_rows, "completion_f1_macro"),
            "completion_accuracy": _metric(svm_rows, "completion_accuracy"),
        },
    }
    summary = {
        "protocol": "strict ten-fold subject-wise LOSO on 387 REAL_VERIFIED samples",
        "seed": SEED,
        "models": models,
        "environment": {
            "python": platform.python_version(),
            "implementation": "numpy",
        },
        "production_changed": False,
    }
    (REPORT_DIR / "classical_baseline_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    lines = [
        "# Classical baseline summary",
        "",
        "Strict ten-fold subject-wise LOSO on the 387 REAL_VERIFIED data-01 samples.",
        "No test fold was used for fitting or tuning.",
        "",
        "| Model | Exercise Macro-F1 | Accuracy | Completion Macro-F1 | Completion accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in (("majority", "Majority Class"), ("linear_svm", "Linear SVM (NumPy)")):
        row = models[key]
        lines.append(
            f"| {label} | {row['exercise_macro_f1']['mean']:.4f} | "
            f"{row['accuracy']['mean']:.4f} | {row['completion_macro_f1']['mean']:.4f} | "
            f"{row['completion_accuracy']['mean']:.4f} |"
        )
    (REPORT_DIR / "CLASSICAL_BASELINE_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
