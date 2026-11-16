"""Compare exploratory optimized-v1 against frozen strict LOSO references."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/evaluation"


def load_rows(filename: str) -> list[dict]:
    payload = json.loads((REPORTS / filename).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "folds" in payload:
        return [{**row, "f1_macro": row["test_f1_macro"], "accuracy": row["test_accuracy"]} for row in payload["folds"]]
    if not isinstance(payload, list):
        raise ValueError(filename)
    return payload


def metric(rows, key):
    values = [float(row[key]) for row in rows]
    return {"mean": statistics.mean(values), "std": statistics.stdev(values), "min": min(values), "max": max(values)}


def main():
    sources = {
        "optimized_v1": "loso_optimized_v1.json",
        "full_v2": "loso_ablation_full.json",
        "ensemble_v1": "loso_ensemble_v1.json",
    }
    rows = {key: load_rows(name) for key, name in sources.items()}
    if any(len(value) != 10 for value in rows.values()):
        raise ValueError("Every candidate must contain ten folds")
    models = {
        key: {"exercise_macro_f1": metric(value, "f1_macro"), "accuracy": metric(value, "accuracy")}
        for key, value in rows.items()
    }
    paired = {}
    for reference in ("full_v2", "ensemble_v1"):
        base = {row["fold_id"]: row for row in rows[reference]}
        deltas = [float(row["f1_macro"]) - float(base[row["fold_id"]]["f1_macro"]) for row in rows["optimized_v1"]]
        paired[reference] = {
            "mean_delta": statistics.mean(deltas),
            "wins": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
            "losses": sum(delta < 0 for delta in deltas),
            "per_fold_delta": dict(zip((row["fold_id"] for row in rows["optimized_v1"]), deltas)),
        }
    # This candidate was designed after observing the ablation test-fold results,
    # so it is exploratory regardless of its score and cannot pass a promotion gate.
    result = {
        "protocol": "strict ten-fold LOSO, seed 42, validation-only checkpoint selection",
        "selection_status": "post_ablation_exploratory",
        "models": models,
        "paired_comparison": paired,
        "promotion_allowed": False,
        "production_changed": False,
        "recommendation": "confirm architecture on additional predeclared seeds or fresh subjects",
    }
    (REPORTS / "optimized_v1_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# Optimized-v1 exploratory result", "",
        "Optimized-v1 keeps pose, hand, kinematic and MS-TCN branches while removing",
        "attention and the frozen contrastive encoder. It uses strict ten-fold LOSO and",
        "validation-only checkpoint selection, but its architecture was chosen after seeing",
        "the ablation results, so this comparison is exploratory.", "",
        "| Model | Exercise Macro-F1 | Accuracy |",
        "|---|---:|---:|",
    ]
    for key, label in (("optimized_v1", "Optimized-v1"), ("full_v2", "Full v2"), ("ensemble_v1", "Ensemble v1")):
        item = models[key]
        lines.append(f"| {label} | {item['exercise_macro_f1']['mean']:.4f} ± {item['exercise_macro_f1']['std']:.4f} | {item['accuracy']['mean']:.4f} ± {item['accuracy']['std']:.4f} |")
    lines += ["", "## Paired evidence", ""]
    for key, label in (("full_v2", "Full v2"), ("ensemble_v1", "Ensemble v1")):
        item = paired[key]
        lines.append(f"- Versus {label}: delta={item['mean_delta']:+.4f}; wins/ties/losses={item['wins']}/{item['ties']}/{item['losses']}.")
    lines += ["", "Production is unchanged. Confirmation on predeclared additional seeds or fresh subjects is required before promotion."]
    (REPORTS / "OPTIMIZED_V1_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
