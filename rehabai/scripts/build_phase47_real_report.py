"""Build traceable Phase 4.7 real-data tables and report from existing artifacts."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "data/stage3_upper_limb/indexes/provenance_verified.csv"
QUALITY = ROOT / "data/stage3_upper_limb/indexes/extraction_quality.csv"
LOSO = ROOT / "data/stage3_upper_limb/loso"
EVALUATION = ROOT / "reports/evaluation/loso_upper_limb_v2.json"
OUT_PROVENANCE = ROOT / "reports/data_provenance"
OUT_EVALUATION = ROOT / "reports/evaluation"


def _metric(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    required = [PROVENANCE, QUALITY, EVALUATION]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 4.7 artifacts: {missing}")

    provenance = pd.read_csv(PROVENANCE, dtype={"subject_id": str})
    quality = pd.read_csv(QUALITY, dtype={"subject_id": str})
    metrics = json.loads(EVALUATION.read_text(encoding="utf-8"))
    if len(provenance) != 387 or len(metrics) != 10:
        raise ValueError("Expected 387 verified samples and ten LOSO folds")
    if set(provenance["data_status"].astype(str)) != {"REAL_VERIFIED"}:
        raise ValueError("Provenance contains non-verified samples")
    if not provenance["source_video_exists"].astype(str).str.lower().eq("true").all():
        raise ValueError("A verified source video is missing")
    if not provenance["processed_exists"].astype(str).str.lower().eq("true").all():
        raise ValueError("A verified processed feature is missing")

    OUT_PROVENANCE.mkdir(parents=True, exist_ok=True)
    OUT_EVALUATION.mkdir(parents=True, exist_ok=True)

    trace = provenance.rename(columns={
        "processed_feature_path": "feature_path",
        "source_video_size": "video_size",
        "source_video_sha256": "video_hash",
        "completion_label": "label",
    })[[
        "feature_path", "source_video_path", "source_video_exists", "video_size",
        "video_hash", "subject_id", "exercise_id", "label", "feature_shape",
        "frame_count", "created_at", "generation_script", "data_status",
        "processed_feature_sha256", "provenance_hash", "verification_evidence",
    ]].copy()
    # Phase 4.7 originally used the historical name h5_provenance.csv.  The
    # current feature contract is NPZ; retain the requested filename and make
    # the actual format explicit in a column.
    trace.insert(1, "feature_format", "npz")
    trace.to_csv(OUT_PROVENANCE / "h5_provenance.csv", index=False)

    label_trace = provenance[[
        "sample_id", "source_record_id", "source_video_path", "subject_id",
        "exercise_id", "completion_label", "label_source", "subject_source",
        "source_video_sha256", "processed_feature_sha256", "data_status",
    ]].copy()
    label_trace.to_csv(OUT_PROVENANCE / "label_provenance.csv", index=False)

    by_fold = {str(row["fold_id"]): row for row in metrics}
    subjects = []
    fold_protocol = []
    for index in range(1, 11):
        fold = f"fold_{index:02d}"
        metadata = json.loads((LOSO / fold / "metadata.json").read_text(encoding="utf-8"))
        row = by_fold[fold]
        subjects.append({
            "subject": metadata["test_subject"],
            "fold_id": fold,
            "accuracy": row["accuracy"],
            "precision": row["precision_macro"],
            "recall": row["recall_macro"],
            "macro_f1": row["f1_macro"],
            "sample_count": row["sample_count"],
            "observed_classes": "|".join(map(str, row["observed_classes"])),
            "class_coverage_complete": row["class_coverage_complete"],
        })
        fold_protocol.append({
            "fold_id": fold,
            "test_subject": metadata["test_subject"],
            "validation_subjects": "|".join(metadata["validation_subjects"]),
            "train_subjects": "|".join(metadata["train_subjects"]),
            "train_samples": metadata["per_split_sample_count"]["train"],
            "validation_samples": metadata["per_split_sample_count"]["val"],
            "test_samples": metadata["per_split_sample_count"]["test"],
            "seed": metadata["seed"],
            "train_manifest_hash": metadata["canonical_train_manifest_hash"],
            "validation_manifest_hash": metadata["canonical_val_manifest_hash"],
            "test_manifest_hash": metadata["canonical_test_manifest_hash"],
            "normalization_scope": "train_only",
            "augmentation_scope": "train_only",
        })
    pd.DataFrame(subjects).to_csv(OUT_EVALUATION / "loso_per_subject.csv", index=False)
    pd.DataFrame(fold_protocol).to_csv(OUT_EVALUATION / "loso_protocol.csv", index=False)

    exercise_f1 = _metric([float(row["f1_macro"]) for row in metrics])
    accuracy = _metric([float(row["accuracy"]) for row in metrics])
    completion_f1 = _metric([float(row["completion_f1_macro"]) for row in metrics])
    completion_accuracy = _metric([float(row["completion_accuracy"]) for row in metrics])
    weighted_f1 = (
        _metric([float(row["f1_weighted"]) for row in metrics])
        if all("f1_weighted" in row for row in metrics)
        else None
    )
    aggregate_confusion = None
    if all("confusion_matrix" in row for row in metrics):
        aggregate_confusion = sum(
            (pd.DataFrame(row["confusion_matrix"], dtype=int) for row in metrics),
            start=pd.DataFrame([[0] * 4 for _ in range(4)], dtype=int),
        )
        aggregate_confusion.index = ["true_1", "true_2", "true_3", "true_4"]
        aggregate_confusion.columns = ["pred_1", "pred_2", "pred_3", "pred_4"]
        aggregate_confusion.to_csv(OUT_EVALUATION / "confusion_matrix_loso.csv")
    status_counts = quality["status"].value_counts().to_dict()
    source_subjects = provenance["subject_id"].nunique()
    exercise_counts = provenance["exercise_id"].value_counts().sort_index().to_dict()
    completion_counts = provenance["completion_label"].value_counts().sort_index().to_dict()

    summary = {
        "status": "PARTIAL",
        "decision": "E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION",
        "source_video_inventory": 491,
        "verified_quality_gate_samples": len(provenance),
        "verified_subjects": int(source_subjects),
        "extraction_status_counts": {str(key): int(value) for key, value in status_counts.items()},
        "exercise_counts": {str(key): int(value) for key, value in exercise_counts.items()},
        "completion_counts": {
            ("complete" if str(key) == "1.0" else "incomplete"): int(value)
            for key, value in completion_counts.items()
        },
        "strict_loso_folds": len(metrics),
        "exercise_macro_f1": exercise_f1,
        "exercise_accuracy": accuracy,
        "exercise_weighted_f1": weighted_f1,
        "completion_macro_f1": completion_f1,
        "completion_accuracy": completion_accuracy,
        "production_model_changed": False,
        "aggregate_confusion_matrix": aggregate_confusion.values.tolist() if aggregate_confusion is not None else None,
    }
    # Generalization-gap diagnostics are derived only from train/validation
    # histories (the test fold is never consulted for checkpoint selection).
    run_root = ROOT / "experiments/upper_limb_v1/training/runs_v2"
    gap_rows = []
    for index in range(1, 11):
        fold = f"fold_{index:02d}"
        summary_path = run_root / f"{fold}_rehab_motionnet_summary.json"
        if not summary_path.is_file():
            continue
        history = json.loads(summary_path.read_text(encoding="utf-8"))
        diagnostics = history.get("diagnostics", {})
        gap_rows.append({
            "fold_id": fold,
            "best_train_f1": max((float(row.get("train_f1", 0.0)) for row in history.get("history", [])), default=0.0),
            "best_val_f1": diagnostics.get("best_val_f1"),
            "final_generalization_gap": diagnostics.get("generalization_gap"),
            "diagnostic_status": diagnostics.get("status"),
            "warnings": "|".join(diagnostics.get("warnings", [])),
        })
    if gap_rows:
        pd.DataFrame(gap_rows).to_csv(OUT_EVALUATION / "loso_generalization_gap.csv", index=False)
        summary["generalization_gap"] = {
            "fold_count": len(gap_rows),
            "mean_final_gap": statistics.mean(float(row["final_generalization_gap"]) for row in gap_rows if row["final_generalization_gap"] is not None),
            "warning_folds": [row["fold_id"] for row in gap_rows if row["diagnostic_status"] == "warning"],
        }
    (OUT_EVALUATION / "phase_4_7_real_data_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    lines = [
        "# Phase 4.7 Real-Data Report (PARTIAL)",
        "",
        "> This version supersedes the historical synthetic-data report for the new",
        "> Stage 3 real-data pipeline. The historical report is retained for audit history.",
        "",
        "## 1. Data Provenance",
        "",
        f"The source index contains 491 real MP4 videos from {source_subjects} subjects. "
        f"The upper-limb quality gate accepted {len(provenance)} samples. Every accepted "
        "NPZ is linked to an existing source video and verified by physical checksums.",
        "",
        "Trace tables: `reports/data_provenance/h5_provenance.csv` (historical filename,",
        "actual feature format is NPZ) and `reports/data_provenance/label_provenance.csv`.",
        "",
        "## 2. Real vs Synthetic Data Verification",
        "",
        "All 387 samples in the training/evaluation manifest have `data_status=REAL_VERIFIED`.",
        "The old mock extraction remains in the repository as a development utility but none",
        "of its artifacts are admitted by the strict manifest loader.",
        "",
        "## 3. Feature Verification",
        "",
        "Strict loading checks exact arrays/shapes, finite values, physical source and processed",
        "file existence, checksums, quality gate and signed provenance before training/evaluation.",
        "",
        "## 4. Label Verification",
        "",
        "Exercise and Complete/Incomplete labels trace to `data/indexes/upper_limb_master.csv`.",
        "No label is inferred or randomly generated.",
        "",
        "## 5. Subject Verification",
        "",
        f"Verified subjects: {source_subjects}. Accepted sample counts by subject are "
        + ", ".join(f"{key}: {value}" for key, value in provenance["subject_id"].value_counts().sort_index().items()) + ".",
        "",
        "## 6. Current Split Audit",
        "",
        "The evaluated pipeline is true ten-fold subject-wise LOSO. Each fold has one test",
        "subject, one validation subject drawn only from the remaining subjects, and eight",
        "training subjects. See `reports/evaluation/loso_protocol.csv`.",
        "",
        "## 7. True LOSO Protocol",
        "",
        "Subject split precedes loading/resampling. Normalization is fitted only on each fold's",
        "training manifest; augmentation is enabled only for training. Manifest and normalization",
        "hashes are checked before model loading and inference.",
        "",
        "## 8. Baseline Results",
        "",
        "The strict MLP baseline is recorded in `reports/evaluation/loso_mlp.json`.",
        "The Phase 4.7 acceptance checklist is not yet fully satisfied: a majority",
        "baseline, classical RF/SVM baseline, simple LSTM baseline, and complete",
        "ablation matrix have not been run under this exact 387-sample LOSO protocol.",
        "Therefore this report is explicitly `PARTIAL`, not a Phase 4.7 PASS.",
        "",
        "## 9. RehabMotionNet Results",
        "",
        "| Metric | Mean | Std | Min | Max |",
        "|---|---:|---:|---:|---:|",
        f"| Exercise Macro-F1 | {exercise_f1['mean']:.4f} | {exercise_f1['std']:.4f} | {exercise_f1['min']:.4f} | {exercise_f1['max']:.4f} |",
        f"| Exercise accuracy | {accuracy['mean']:.4f} | {accuracy['std']:.4f} | {accuracy['min']:.4f} | {accuracy['max']:.4f} |",
        f"| Exercise weighted-F1 | {weighted_f1['mean']:.4f} | {weighted_f1['std']:.4f} | {weighted_f1['min']:.4f} | {weighted_f1['max']:.4f} |" if weighted_f1 else "| Exercise weighted-F1 | pending re-evaluation | - | - | - |",
        f"| Completion Macro-F1 | {completion_f1['mean']:.4f} | {completion_f1['std']:.4f} | {completion_f1['min']:.4f} | {completion_f1['max']:.4f} |",
        f"| Completion accuracy | {completion_accuracy['mean']:.4f} | {completion_accuracy['std']:.4f} | {completion_accuracy['min']:.4f} | {completion_accuracy['max']:.4f} |",
        "",
        "## 10. Per-Fold and Per-Subject Results",
        "",
        "Machine-readable per-fold results are in `loso_upper_limb_v2.json`; the derived",
        "per-subject table is `loso_per_subject.csv`. No difficult fold is removed.",
        "",
        "## 11. Generalization and Failure Analysis",
        "",
        "Performance varies strongly by subject. Subjects 07-10 contain only one canonical",
        "exercise each after source/quality constraints, so four-class Macro-F1 correctly",
        "penalizes the unavailable class coverage. This is the dominant scientific limitation.",
        "",
        "## 12. Limitations",
        "",
        "Only ten subjects and 387 accepted samples are available. One seed (42) was used.",
        "Completion labels mean Complete/Incomplete, not clinical correctness. The current",
        "runtime environment is Python 3.11.9, PyTorch 2.5.1+cu121 and MediaPipe 0.10.9,",
        "which does not match the canonical V3.1 lock (PyTorch 2.7.0+cu126, MediaPipe 1.0.1).",
        "Existing model metrics must therefore be described with their actual environment.",
        "",
        "## 13. Final Decision",
        "",
        "**E. DATASET TOO SMALL / INSUFFICIENT FOR STRONG CONCLUSION.**",
        "",
        "The real-data pipeline and strict LOSO protocol are valid for research evaluation,",
        "but the sample/subject/class coverage is insufficient for a clinical or robust",
        "generalization claim. Production remains unchanged.",
    ]
    (OUT_EVALUATION / "PHASE_4_7_REAL_DATA_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
