"""Summarize paired external-pretraining ablations without promotion."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "evaluation"


def load(name: str):
    rows = json.loads((REPORTS / name).read_text(encoding="utf-8"))
    return rows["folds"] if isinstance(rows, dict) else rows


def stats(rows, key):
    values = [float(row[key]) for row in rows]
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values),
        "min": min(values),
        "max": max(values),
    }


def main():
    sources = {
        "rehab24_only": ("REHAB24-6 only (02)", "loso_external_pretraining_rehab24_only.json"),
        "mobiphysio_only": ("MobiPhysio only (03)", "loso_external_pretraining_mobiphysio_only.json"),
        "combined": ("02 + 03", "loso_external_pretraining_v1.json"),
        "v2": ("Existing RehabMotionNet v2", "loso_upper_limb_v2.json"),
        "ensemble": ("Existing validation-selected ensemble", "loso_ensemble_v1.json"),
        "teacher_student": ("Existing teacher-student", "loso_teacher_student_v1.json"),
    }
    result = {"protocol": "paired strict ten-fold subject-wise LOSO", "models": {}, "folds": {}}
    loaded = {}
    for key, (label, filename) in sources.items():
        rows = load(filename)
        loaded[key] = rows
        fkey = "f1_macro" if "f1_macro" in rows[0] else "test_f1_macro"
        akey = "accuracy" if "accuracy" in rows[0] else "test_accuracy"
        result["models"][key] = {
            "label": label,
            "exercise_macro_f1": stats(rows, fkey),
            "accuracy": stats(rows, akey),
            "completion_macro_f1": stats(rows, "completion_f1_macro") if "completion_f1_macro" in rows[0] else None,
            "completion_accuracy": stats(rows, "completion_accuracy") if "completion_accuracy" in rows[0] else None,
        }
    for i in range(10):
        fold = loaded["combined"][i]["fold_id"]
        result["folds"][fold] = {
            key: float(row.get("f1_macro", row.get("test_f1_macro")))
            for key, rows in loaded.items()
            for row in rows[i:i + 1]
        }
    result["recommendation"] = "keep_existing_ensemble_for_research; do_not_promote_external_pretraining"
    result["reason"] = (
        "Combined 02+03 and each single-source ablation are below existing v2/ensemble "
        "on mean exercise Macro-F1 and accuracy."
    )
    (REPORTS / "external_pretraining_ablation_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    rows = []
    for key in ["rehab24_only", "mobiphysio_only", "combined", "v2", "ensemble", "teacher_student"]:
        model = result["models"][key]
        f1 = model["exercise_macro_f1"]
        acc = model["accuracy"]
        rows.append(f"| {model['label']} | {f1['mean']:.4f} | {f1['std']:.4f} | {acc['mean']:.4f} | {acc['std']:.4f} |")
    md = "\n".join([
        "# External-pretraining ablation summary",
        "",
        "All figures use the same strict ten-fold subject-wise LOSO test protocol on data 01.",
        "No test fold was used for checkpoint or hyperparameter selection.",
        "",
        "| Model | Exercise Macro-F1 mean | F1 std | Accuracy mean | Accuracy std |",
        "|---|---:|---:|---:|---:|",
        *rows,
        "",
        "## Decision",
        "",
        "The external-pretraining branches remain research artifacts and are not promoted.",
        "The combined 02+03 branch is below the existing v2 and validation-selected ensemble.",
        "The single-source ablations do not recover the loss, so the issue is not explained by",
        "simple source mixing alone; domain/ontology mismatch and limited target data remain likely.",
        "Production remains unchanged.",
        "",
        "Recommended next experiment: freeze the external encoder and train only a small target",
        "adapter or use external data for self-supervised motion objectives without source-exercise",
        "classification heads, then repeat the same paired LOSO evaluation.",
    ])
    (REPORTS / "EXTERNAL_PRETRAINING_ABLATION_SUMMARY.md").write_text(md + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
