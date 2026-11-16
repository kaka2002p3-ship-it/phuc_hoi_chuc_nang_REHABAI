"""Compare the external-pretrained candidate with the existing strict LOSO results."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "evaluation"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _mean(rows, key: str) -> float:
    return statistics.mean(float(row[key]) for row in rows)


def main() -> None:
    candidate_path = REPORTS / "loso_external_pretraining_v1.json"
    v2_path = REPORTS / "loso_upper_limb_v2.json"
    ensemble_path = REPORTS / "loso_ensemble_v1.json"
    candidate = _read(candidate_path)
    v2 = _read(v2_path)
    ensemble = _read(ensemble_path)

    if len(candidate) != 10 or len(v2) != 10 or len(ensemble.get("folds", [])) != 10:
        raise ValueError("Comparison requires ten complete folds for every candidate")
    by_candidate = {row["fold_id"]: row for row in candidate}
    by_v2 = {row["fold_id"]: row for row in v2}
    by_ensemble = {row["fold_id"]: row for row in ensemble["folds"]}
    if set(by_candidate) != set(by_v2) or set(by_candidate) != set(by_ensemble):
        raise ValueError("Fold identities differ between LOSO reports")

    folds = []
    for fold in sorted(by_candidate):
        new = by_candidate[fold]
        old = by_v2[fold]
        ens = by_ensemble[fold]
        folds.append({
            "fold_id": fold,
            "external_f1_macro": float(new["f1_macro"]),
            "v2_f1_macro": float(old["f1_macro"]),
            "ensemble_f1_macro": float(ens["test_f1_macro"]),
            "delta_f1_vs_v2": float(new["f1_macro"] - old["f1_macro"]),
            "delta_f1_vs_ensemble": float(new["f1_macro"] - ens["test_f1_macro"]),
            "external_accuracy": float(new["accuracy"]),
            "v2_accuracy": float(old["accuracy"]),
            "ensemble_accuracy": float(ens["test_accuracy"]),
        })

    external_f1 = [row["external_f1_macro"] for row in folds]
    external_accuracy = [row["external_accuracy"] for row in folds]
    mean_f1 = statistics.mean(external_f1)
    std_f1 = statistics.stdev(external_f1)
    mean_accuracy = statistics.mean(external_accuracy)
    ensemble_f1 = float(ensemble["mean_test_f1_macro"])
    ensemble_accuracy = float(ensemble["mean_test_accuracy"])
    ensemble_std = float(ensemble["std_test_f1_macro"])
    hard = [row for row in folds if row["fold_id"] in {"fold_07", "fold_08", "fold_09", "fold_10"}]
    hard_external = _mean(hard, "external_f1_macro")
    hard_ensemble = _mean(hard, "ensemble_f1_macro")

    gates = {
        "macro_f1_above_ensemble": mean_f1 > ensemble_f1,
        "accuracy_not_lower_by_more_than_0_01": mean_accuracy >= ensemble_accuracy - 0.01,
        "fold_std_below_ensemble": std_f1 < ensemble_std,
        "hard_fold_mean_not_lower": hard_external >= hard_ensemble,
        "all_folds_have_external_provenance": all(
            row.get("metadata", {}).get("training_inputs", {}).get("external_encoder")
            for row in candidate
        ),
    }
    promote = all(gates.values())
    output = {
        "comparison": "strict paired ten-fold subject-wise LOSO; no test-set model selection",
        "candidate": "RehabMotionNet_v2_external_pretraining_02_03",
        "folds": folds,
        "summary": {
            "external_mean_f1_macro": mean_f1,
            "external_std_f1_macro": std_f1,
            "external_mean_accuracy": mean_accuracy,
            "ensemble_mean_f1_macro": ensemble_f1,
            "ensemble_std_f1_macro": ensemble_std,
            "ensemble_mean_accuracy": ensemble_accuracy,
            "mean_delta_f1_vs_v2": _mean(folds, "delta_f1_vs_v2"),
            "mean_delta_f1_vs_ensemble": _mean(folds, "delta_f1_vs_ensemble"),
            "external_better_than_v2_folds": sum(row["delta_f1_vs_v2"] > 0 for row in folds),
            "external_better_than_ensemble_folds": sum(row["delta_f1_vs_ensemble"] > 0 for row in folds),
            "hard_fold_external_mean_f1": hard_external,
            "hard_fold_ensemble_mean_f1": hard_ensemble,
        },
        "promotion_gates": gates,
        "recommendation": (
            "external_pretraining_is_stronger_research_candidate"
            if promote else "keep_existing_model_and_run_external_ablation"
        ),
        "production_promoted": False,
    }
    output_path = REPORTS / "external_pretraining_vs_existing.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    s = output["summary"]
    lines = [
        "# External pretraining decision",
        "",
        "Evaluation uses the unchanged data-01 strict ten-fold LOSO test sets.",
        "External data is used only to initialize the shared encoder.",
        "",
        "| Model | Mean Macro-F1 | Fold std | Mean accuracy |",
        "|---|---:|---:|---:|",
        f"| External pretraining 02+03 | {s['external_mean_f1_macro']:.4f} | {s['external_std_f1_macro']:.4f} | {s['external_mean_accuracy']:.4f} |",
        f"| Existing ensemble | {s['ensemble_mean_f1_macro']:.4f} | {s['ensemble_std_f1_macro']:.4f} | {s['ensemble_mean_accuracy']:.4f} |",
        "",
        f"Recommendation: `{output['recommendation']}`.",
        "",
        "The production artifact is not changed automatically. External-only ablations and",
        "fresh-subject validation remain required before any production promotion.",
    ]
    (REPORTS / "EXTERNAL_PRETRAINING_DECISION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
