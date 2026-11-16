"""Summarize strict LOSO ablations without promoting a model."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/evaluation"
VARIANTS = ["full", "minus_hand", "minus_kinematic", "minus_contrastive", "minus_mstcn", "minus_attention"]


def stats(rows, key):
    values = [float(row[key]) for row in rows]
    return {"mean": statistics.mean(values), "std": statistics.stdev(values), "min": min(values), "max": max(values)}


def main():
    result = {"protocol": "strict subject-wise ten-fold LOSO; seed 42; validation-only selection", "variants": {}, "production_changed": False}
    for variant in VARIANTS:
        path = REPORTS / f"loso_ablation_{variant}.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or len(rows) != 10:
            raise ValueError(f"{path} must contain exactly ten fold results")
        result["variants"][variant] = {
            "exercise_macro_f1": stats(rows, "f1_macro"),
            "accuracy": stats(rows, "accuracy"),
            "weighted_f1": stats(rows, "f1_weighted"),
            "completion_macro_f1": stats(rows, "completion_f1_macro"),
            "completion_accuracy": stats(rows, "completion_accuracy"),
            "folds": rows,
        }
    full = result["variants"]["full"]["exercise_macro_f1"]["mean"]
    result["delta_vs_full"] = {
        key: value["exercise_macro_f1"]["mean"] - full
        for key, value in result["variants"].items()
    }
    full_rows = {row["fold_id"]: row for row in result["variants"]["full"]["folds"]}
    result["paired_vs_full"] = {}
    for key, value in result["variants"].items():
        deltas = [
            float(row["f1_macro"]) - float(full_rows[row["fold_id"]]["f1_macro"])
            for row in value["folds"]
        ]
        result["paired_vs_full"][key] = {
            "fold_wins": sum(delta > 0 for delta in deltas),
            "fold_ties": sum(delta == 0 for delta in deltas),
            "fold_losses": sum(delta < 0 for delta in deltas),
            "per_fold_delta": dict(zip((row["fold_id"] for row in value["folds"]), deltas)),
        }
    result["best_variant_by_macro_f1"] = max(result["variants"], key=lambda key: result["variants"][key]["exercise_macro_f1"]["mean"])
    (REPORTS / "ablation_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# RehabMotionNet strict ablation summary", "",
        "All variants use the same 387 REAL_VERIFIED samples, ten-fold LOSO, seed 42,",
        "train-only normalization/augmentation and validation-only checkpoint selection.", "",
        "| Variant | Exercise Macro-F1 | Accuracy | Weighted-F1 | Completion Macro-F1 | Completion accuracy | Delta vs full | W/T/L |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {"full":"Full", "minus_hand":"− hand", "minus_kinematic":"− kinematic", "minus_contrastive":"− contrastive", "minus_mstcn":"− MS-TCN", "minus_attention":"− attention"}
    for key in VARIANTS:
        item = result["variants"][key]
        lines.append(
            f"| {labels[key]} | {item['exercise_macro_f1']['mean']:.4f} ± {item['exercise_macro_f1']['std']:.4f} | "
            f"{item['accuracy']['mean']:.4f} ± {item['accuracy']['std']:.4f} | "
            f"{item['weighted_f1']['mean']:.4f} ± {item['weighted_f1']['std']:.4f} | "
            f"{item['completion_macro_f1']['mean']:.4f} ± {item['completion_macro_f1']['std']:.4f} | "
            f"{item['completion_accuracy']['mean']:.4f} ± {item['completion_accuracy']['std']:.4f} | "
            f"{result['delta_vs_full'][key]:+.4f} | "
            f"{result['paired_vs_full'][key]['fold_wins']}/"
            f"{result['paired_vs_full'][key]['fold_ties']}/"
            f"{result['paired_vs_full'][key]['fold_losses']} |"
        )
    best = result["best_variant_by_macro_f1"]
    paired = result["paired_vs_full"][best]
    lines += [
        "", f"Best ablation by mean exercise Macro-F1: `{best}`.",
        f"It wins/ties/loses {paired['fold_wins']}/{paired['fold_ties']}/{paired['fold_losses']} folds against full.",
        "The mean gain is exploratory and not fold-stable; it is not sufficient for promotion.",
        "Production remains unchanged; ablations are research artifacts. The next optimization",
        "should confirm the simplified candidate across additional seeds or fresh subjects before",
        "any architecture decision.",
    ]
    (REPORTS / "ABLATION_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"best_variant": result["best_variant_by_macro_f1"], "delta_vs_full": result["delta_vs_full"]}, indent=2))


if __name__ == "__main__":
    main()
