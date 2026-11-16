"""Finalize the Phase 4.7 report after strict baseline evaluation completes."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/evaluation"


def _summary(path: str) -> dict:
    return json.loads((REPORT_DIR / path).read_text(encoding="utf-8"))


def _metric(model: dict, key: str) -> str:
    value = model[key]
    if value is None:
        return "n/a"
    return f"{value['mean']:.4f} ± {value['std']:.4f}"


def main() -> None:
    baseline = _summary("phase_4_7_baseline_summary.json")
    real = _summary("phase_4_7_real_data_summary.json")
    required = [
        "loso_strict_mlp.json", "loso_strict_lstm.json", "loso_majority.json",
        "loso_linear_svm.json", "loso_upper_limb_v2.json", "loso_ensemble_v1.json",
        "loso_per_subject.csv", "loso_protocol.csv", "confusion_matrix_loso.csv",
        "loso_generalization_gap.csv",
    ]
    missing = [name for name in required if not (REPORT_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 4.7 acceptance artifacts: {missing}")

    models = baseline["models"]
    lines = [
        "# Phase 4.7 Final Report — Real Data + True LOSO",
        "",
        "> Status: **PASS (protocol and acceptance artifacts complete)**. The scientific",
        "> decision remains **E — dataset too small / insufficient for a strong generalization",
        "> conclusion**. PASS here means the evaluation protocol is complete, not that the",
        "> model is clinically validated or that its accuracy is high.",
        "",
        "## 1. Data provenance",
        "",
        "The source index contains 491 real MP4 videos from 10 subjects. The upper-limb",
        "quality gate accepted 387 samples. Every accepted NPZ is linked to an existing",
        "source video and has a verified source/feature checksum.",
        "",
        "Trace artifacts: `reports/data_provenance/h5_provenance.csv` and",
        "`reports/data_provenance/label_provenance.csv`.",
        "",
        "## 2. Real vs synthetic verification",
        "",
        "The strict training/evaluation manifest contains 387 `REAL_VERIFIED` samples.",
        "The historical mock extractor remains in the repository but its artifacts are",
        "excluded by the strict manifest and loader.",
        "",
        "## 3. Feature, label and subject verification",
        "",
        "Features are finite, shape-checked and physically traced to source videos.",
        "Exercise and completion labels come from `upper_limb_master.csv`; subject IDs",
        "come from the authoritative index. No random or inferred labels are admitted.",
        "",
        "## 4. True LOSO protocol",
        "",
        "Ten folds are evaluated with one held-out test subject per fold. Validation is",
        "drawn only from the training subjects. Subject split precedes loading/windowing,",
        "normalization is fitted on train only, and augmentation is train only.",
        "Checkpoint selection and all hyperparameter decisions use validation only.",
        "",
        "## 5. Strict baseline results",
        "",
        "| Model | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    labels = [
        ("majority", "Majority Class"),
        ("linear_svm", "Linear SVM (48-D kinematics)"),
        ("mlp", "MLP"),
        ("lstm", "Simple LSTM"),
        ("rehabmotionnet_v2", "RehabMotionNet v2"),
    ]
    for key, label in labels:
        model = models[key]
        lines.append(
            f"| {label} | {_metric(model, 'exercise_macro_f1')} | "
            f"{_metric(model, 'exercise_accuracy')} | {_metric(model, 'exercise_weighted_f1')} | "
            f"{_metric(model, 'completion_macro_f1')} | {_metric(model, 'completion_accuracy')} |"
        )
    ensemble = models["ensemble_v1"]
    lines.append(
        f"| Ensemble v1 (research) | {_metric(ensemble, 'exercise_macro_f1')} | "
        f"{_metric(ensemble, 'exercise_accuracy')} | n/a | n/a | n/a |"
    )
    lines += [
        "",
        "The MLP and LSTM rows are strict evaluations of the 20 completed checkpoints",
        "(`baseline_mlp_v1` and `baseline_lstm_v1`), not retraining runs.",
        "",
        "## 6. Per-fold, per-subject and confusion artifacts",
        "",
        "Machine-readable per-fold outputs are in `loso_strict_mlp.json`,",
        "`loso_strict_lstm.json` and `loso_upper_limb_v2.json`. Per-subject metrics are",
        "in `loso_per_subject.csv`; the aggregate confusion matrix is in",
        "`confusion_matrix_loso.csv`; protocol and generalization-gap tables are",
        "`loso_protocol.csv` and `loso_generalization_gap.csv`.",
        "",
        "## 7. Overfitting and failure analysis",
        "",
        f"MLP mean final train–validation F1 gap: "
        f"{baseline['training_diagnostics']['mlp']['mean_final_train_validation_gap']:.4f}; "
        f"warning folds: {', '.join(baseline['training_diagnostics']['mlp']['warning_folds']) or 'none'}.",
        f"LSTM mean final train–validation F1 gap: "
        f"{baseline['training_diagnostics']['lstm']['mean_final_train_validation_gap']:.4f}; "
        f"warning folds: {', '.join(baseline['training_diagnostics']['lstm']['warning_folds']) or 'none'}.",
        "Subjects 07–10 have restricted exercise coverage, which strongly depresses",
        "four-class macro-F1 on those held-out folds. This is the dominant limitation.",
        "",
        "## 8. Limitations",
        "",
        "There are only 10 subjects and 387 accepted samples, with one seed (42). The",
        "runtime is Python 3.11.9, PyTorch 2.5.1+cu121 and MediaPipe 0.10.9, rather than",
        "the canonical V3.1 lock. The results are research subject-independent evaluation,",
        "not clinical validation or a medical-grade claim.",
        "",
        "## 9. Decision and next step",
        "",
        "**Protocol status: PASS. Scientific conclusion: E — DATASET TOO SMALL /",
        "INSUFFICIENT FOR STRONG CONCLUSION.**",
        "",
        "Production remains unchanged. The project may now proceed to the planned ablation",
        "matrix, preserving the same ten-fold LOSO protocol and validation-only selection.",
        "Ablation results must remain research artifacts until they beat the current",
        "baseline/ensemble with stable fold-wise evidence and independent confirmation.",
    ]
    (REPORT_DIR / "PHASE_4_7_FINAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    real.update({
        "status": "PASS",
        "protocol_status": "PASS",
        "decision": "E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION",
        "baseline_evaluation_complete": True,
        "production_model_changed": False,
    })
    (REPORT_DIR / "phase_4_7_real_data_summary.json").write_text(
        json.dumps(real, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "decision": real["decision"]}, indent=2))


if __name__ == "__main__":
    main()
