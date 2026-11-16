"""Summarize the frozen IntelliRehab SSL transfer pilot without promotion."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/evaluation"


def rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 10:
        raise ValueError(f"Expected ten LOSO rows in {path}")
    return payload


def stats(items: list[dict], key: str) -> dict:
    values = [float(row[key]) for row in items]
    return {"mean": statistics.mean(values), "std": statistics.stdev(values), "min": min(values), "max": max(values)}


def main() -> None:
    candidate = rows(REPORTS / "loso_intellirehab_ssl_adapter_v1.json")
    optimized = rows(REPORTS / "loso_optimized_v1.json")
    baseline = {row["fold_id"]: row for row in optimized}
    deltas = [float(row["f1_macro"]) - float(baseline[row["fold_id"]]["f1_macro"]) for row in candidate]
    result = {
        "protocol": "strict ten-fold subject-wise LOSO, seed 42, validation-only checkpoint selection",
        "candidate": "Optimized-v1 + frozen IntelliRehabDS SSL encoder (fold 0 predeclared)",
        "candidate_metrics": {"exercise_macro_f1": stats(candidate, "f1_macro"), "accuracy": stats(candidate, "accuracy")},
        "optimized_v1_reference": {"exercise_macro_f1": stats(optimized, "f1_macro"), "accuracy": stats(optimized, "accuracy")},
        "paired_vs_optimized_v1": {
            "mean_delta": statistics.mean(deltas),
            "median_delta": statistics.median(deltas),
            "wins": sum(delta > 0 for delta in deltas),
            "ties": sum(delta == 0 for delta in deltas),
            "losses": sum(delta < 0 for delta in deltas),
            "per_fold_delta": dict(zip((row["fold_id"] for row in candidate), deltas)),
        },
        "selection_status": "predeclared_exploratory_pilot",
        "promotion_allowed": False,
        "production_changed": False,
        "recommendation": "keep Optimized-v1 until fresh-subject validation and additional predeclared seeds",
    }
    (REPORTS / "intellirehab_ssl_adapter_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# IntelliRehabDS SSL adapter pilot", "",
        "This is a frozen fold-0 self-supervised IntelliRehabDS encoder attached to the predeclared Optimized-v1 target model.",
        "It is exploratory and does not change production.", "",
        "| Model | Exercise Macro-F1 | Accuracy |", "|---|---:|---:|",
        f"| SSL adapter | {result['candidate_metrics']['exercise_macro_f1']['mean']:.4f} ± {result['candidate_metrics']['exercise_macro_f1']['std']:.4f} | {result['candidate_metrics']['accuracy']['mean']:.4f} ± {result['candidate_metrics']['accuracy']['std']:.4f} |",
        f"| Optimized-v1 | {result['optimized_v1_reference']['exercise_macro_f1']['mean']:.4f} ± {result['optimized_v1_reference']['exercise_macro_f1']['std']:.4f} | {result['optimized_v1_reference']['accuracy']['mean']:.4f} ± {result['optimized_v1_reference']['accuracy']['std']:.4f} |",
        "", f"Paired Macro-F1 delta: {result['paired_vs_optimized_v1']['mean_delta']:+.4f}; wins/ties/losses={result['paired_vs_optimized_v1']['wins']}/{result['paired_vs_optimized_v1']['ties']}/{result['paired_vs_optimized_v1']['losses']}.",
        "", "Production remains unchanged; fresh-subject validation is required before promotion.", "",
    ]
    (REPORTS / "INTELLIREHAB_SSL_ADAPTER_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
