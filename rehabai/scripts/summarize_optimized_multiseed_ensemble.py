"""Compare the equal-weight multi-seed ensemble against frozen references."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/evaluation"


def load(name):
    rows = json.loads((REPORTS / name).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError(f"Expected ten folds in {name}")
    return rows


def metric(rows, key):
    values = [float(row[key]) for row in rows]
    return {"mean": statistics.mean(values), "std": statistics.stdev(values), "min": min(values), "max": max(values)}


def paired(candidate, reference):
    base = {row["fold_id"]: row for row in reference}
    deltas = [float(row["f1_macro"]) - float(base[row["fold_id"]]["f1_macro"]) for row in candidate]
    return {"mean_delta": statistics.mean(deltas), "median_delta": statistics.median(deltas),
            "wins": sum(x > 0 for x in deltas), "ties": sum(x == 0 for x in deltas),
            "losses": sum(x < 0 for x in deltas),
            "per_fold_delta": dict(zip((row["fold_id"] for row in candidate), deltas))}


def main():
    ensemble = load("loso_optimized_v1_multiseed_ensemble.json")
    seed42 = load("loso_optimized_v1.json")
    seed7 = load("loso_optimized_v1_seed_7.json")
    seed2026 = load("loso_optimized_v1_seed_2026.json")
    references = {"seed_42": seed42, "seed_7": seed7, "seed_2026": seed2026}
    result = {
        "protocol": "strict ten-fold LOSO; equal probability mean; no training or test-fold weight selection",
        "selection_status": "post_hoc_exploratory_reuse_of_predeclared_seed_checkpoints",
        "ensemble": {"exercise_macro_f1": metric(ensemble, "f1_macro"),
                     "accuracy": metric(ensemble, "accuracy"),
                     "completion_macro_f1": metric(ensemble, "completion_f1_macro")},
        "references": {name: {"exercise_macro_f1": metric(rows, "f1_macro"), "accuracy": metric(rows, "accuracy")}
                       for name, rows in references.items()},
        "paired": {name: paired(ensemble, rows) for name, rows in references.items()},
        "promotion_allowed": False,
        "production_changed": False,
        "fresh_subject_validation_required": True,
    }
    (REPORTS / "optimized_v1_multiseed_ensemble_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = ["# Optimized-v1 multi-seed ensemble", "",
             "Equal softmax-probability averaging of the existing seed 42, 7 and 2026 checkpoints.",
             "No new training and no test-fold weight selection were used.", "",
             "| Candidate | Macro-F1 | Accuracy |", "|---|---:|---:|",
             f"| Three-seed ensemble | {result['ensemble']['exercise_macro_f1']['mean']:.4f} ± {result['ensemble']['exercise_macro_f1']['std']:.4f} | {result['ensemble']['accuracy']['mean']:.4f} ± {result['ensemble']['accuracy']['std']:.4f} |"]
    for name in references:
        item = result["references"][name]
        lines.append(f"| {name.replace('_', ' ')} | {item['exercise_macro_f1']['mean']:.4f} ± {item['exercise_macro_f1']['std']:.4f} | {item['accuracy']['mean']:.4f} ± {item['accuracy']['std']:.4f} |")
    lines += ["", "## Paired result", ""]
    for name, item in result["paired"].items():
        lines.append(f"- Versus {name}: delta={item['mean_delta']:+.4f}; W/T/L={item['wins']}/{item['ties']}/{item['losses']}.")
    lines += ["", "This remains exploratory. Production is unchanged and fresh-subject validation is required.", ""]
    (REPORTS / "OPTIMIZED_V1_MULTISEED_ENSEMBLE_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
