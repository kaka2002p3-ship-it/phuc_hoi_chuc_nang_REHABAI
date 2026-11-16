"""Summarize all strict Phase 4.7 baselines and the current research candidates."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/evaluation"
RUN_DIR = ROOT / "experiments/strict_baselines/runs"


def _read(name: str):
    path = REPORT_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing evaluation artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _stats(rows: list[dict], key: str) -> dict[str, float]:
    values = [float(row[key]) for row in rows]
    if len(values) != 10:
        raise ValueError(f"Expected ten folds for {key}, got {len(values)}")
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values),
        "min": min(values),
        "max": max(values),
    }


def _summarize_rows(rows: list[dict]) -> dict:
    required = {
        "f1_macro", "accuracy", "f1_weighted",
        "completion_f1_macro", "completion_accuracy",
    }
    for row in rows:
        missing = required - set(row)
        if missing:
            raise ValueError(f"{row.get('fold_id')} is missing metrics: {sorted(missing)}")
    return {
        "exercise_macro_f1": _stats(rows, "f1_macro"),
        "exercise_accuracy": _stats(rows, "accuracy"),
        "exercise_weighted_f1": _stats(rows, "f1_weighted"),
        "completion_macro_f1": _stats(rows, "completion_f1_macro"),
        "completion_accuracy": _stats(rows, "completion_accuracy"),
        "folds": [{
            "fold_id": row["fold_id"],
            "sample_count": int(row["sample_count"]),
            "exercise_macro_f1": float(row["f1_macro"]),
            "exercise_accuracy": float(row["accuracy"]),
            "exercise_weighted_f1": float(row["f1_weighted"]),
            "completion_macro_f1": float(row["completion_f1_macro"]),
            "completion_accuracy": float(row["completion_accuracy"]),
        } for row in rows],
    }


def _training_diagnostics(model_name: str) -> dict:
    rows = []
    for fold_number in range(1, 11):
        fold_id = f"fold_{fold_number:02d}"
        path = RUN_DIR / f"{fold_id}_baseline_{model_name}_summary.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing training summary: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        diagnostics = payload.get("diagnostics", {})
        rows.append({
            "fold_id": fold_id,
            "best_epoch": diagnostics.get("best_epoch"),
            "best_validation_f1": diagnostics.get("best_val_f1"),
            "final_train_validation_gap": diagnostics.get("generalization_gap"),
            "status": diagnostics.get("status"),
            "warnings": diagnostics.get("warnings", []),
        })
    gaps = [float(row["final_train_validation_gap"]) for row in rows
            if row["final_train_validation_gap"] is not None]
    return {
        "folds": rows,
        "mean_final_train_validation_gap": statistics.mean(gaps) if gaps else None,
        "warning_folds": [row["fold_id"] for row in rows if row["status"] == "warning"],
    }


def _line(label: str, result: dict) -> str:
    return (
        f"| {label} | {result['exercise_macro_f1']['mean']:.4f} ± "
        f"{result['exercise_macro_f1']['std']:.4f} | "
        f"{result['exercise_accuracy']['mean']:.4f} ± {result['exercise_accuracy']['std']:.4f} | "
        f"{result['exercise_weighted_f1']['mean']:.4f} ± {result['exercise_weighted_f1']['std']:.4f} | "
        f"{result['completion_macro_f1']['mean']:.4f} ± {result['completion_macro_f1']['std']:.4f} | "
        f"{result['completion_accuracy']['mean']:.4f} ± {result['completion_accuracy']['std']:.4f} |"
    )


def main() -> None:
    sources = {
        "majority": ("Majority Class", "loso_majority.json"),
        "linear_svm": ("Linear SVM (48-D kinematics)", "loso_linear_svm.json"),
        "mlp": ("MLP", "loso_strict_mlp.json"),
        "lstm": ("Simple LSTM", "loso_strict_lstm.json"),
        "rehabmotionnet_v2": ("RehabMotionNet v2", "loso_upper_limb_v2.json"),
    }
    results = {}
    for key, (_, filename) in sources.items():
        rows = _read(filename)
        if not isinstance(rows, list):
            raise ValueError(f"Expected fold list in {filename}")
        results[key] = _summarize_rows(rows)

    ensemble = _read("loso_ensemble_v1.json")
    ensemble_folds = ensemble.get("folds", [])
    if len(ensemble_folds) != 10:
        raise ValueError("Expected ten ensemble folds")
    ensemble_f1 = [float(row["test_f1_macro"]) for row in ensemble_folds]
    ensemble_acc = [float(row["test_accuracy"]) for row in ensemble_folds]
    results["ensemble_v1"] = {
        "exercise_macro_f1": {
            "mean": statistics.mean(ensemble_f1), "std": statistics.stdev(ensemble_f1),
            "min": min(ensemble_f1), "max": max(ensemble_f1),
        },
        "exercise_accuracy": {
            "mean": statistics.mean(ensemble_acc), "std": statistics.stdev(ensemble_acc),
            "min": min(ensemble_acc), "max": max(ensemble_acc),
        },
        "exercise_weighted_f1": None,
        "completion_macro_f1": None,
        "completion_accuracy": None,
        "folds": ensemble_folds,
        "note": "Validation-selected research ensemble; completion head is unavailable.",
    }

    payload = {
        "protocol": "strict subject-wise ten-fold LOSO on 387 REAL_VERIFIED data-01 samples",
        "seed": 42,
        "selection_rule": "checkpoint selected on validation only; test subject never used for tuning",
        "models": results,
        "training_diagnostics": {
            "mlp": _training_diagnostics("mlp"),
            "lstm": _training_diagnostics("lstm"),
        },
        "best_single_model_by_exercise_macro_f1": max(
            (key for key in sources),
            key=lambda key: results[key]["exercise_macro_f1"]["mean"],
        ),
        "best_research_candidate_by_exercise_macro_f1": max(
            results, key=lambda key: results[key]["exercise_macro_f1"]["mean"]
        ),
        "production_changed": False,
    }
    (REPORT_DIR / "phase_4_7_baseline_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    lines = [
        "# Phase 4.7 strict LOSO baseline summary",
        "",
        "All trainable checkpoints were selected using validation data only and evaluated",
        "once on the held-out subject. Results cover all ten folds and 387 REAL_VERIFIED samples.",
        "",
        "| Model | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, (label, _) in sources.items():
        lines.append(_line(label, results[key]))
    ensemble_result = results["ensemble_v1"]
    lines.append(
        f"| Ensemble v1 (research) | {ensemble_result['exercise_macro_f1']['mean']:.4f} ± "
        f"{ensemble_result['exercise_macro_f1']['std']:.4f} | "
        f"{ensemble_result['exercise_accuracy']['mean']:.4f} ± "
        f"{ensemble_result['exercise_accuracy']['std']:.4f} | n/a | n/a | n/a |"
    )
    lines += [
        "",
        "## Range and stability",
        "",
        "| Model | Exercise Macro-F1 min | max |",
        "|---|---:|---:|",
    ]
    for key, (label, _) in sources.items():
        metric = results[key]["exercise_macro_f1"]
        lines.append(f"| {label} | {metric['min']:.4f} | {metric['max']:.4f} |")
    metric = ensemble_result["exercise_macro_f1"]
    lines.append(f"| Ensemble v1 (research) | {metric['min']:.4f} | {metric['max']:.4f} |")
    lines += [
        "",
        "## Decision",
        "",
        f"Best single model: `{payload['best_single_model_by_exercise_macro_f1']}`.",
        f"Best research candidate: `{payload['best_research_candidate_by_exercise_macro_f1']}`.",
        "The production artifact is unchanged. Model optimization and ablation must retain",
        "the same strict protocol, and no promotion is allowed without stronger evidence.",
    ]
    (REPORT_DIR / "PHASE_4_7_BASELINE_SUMMARY.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
