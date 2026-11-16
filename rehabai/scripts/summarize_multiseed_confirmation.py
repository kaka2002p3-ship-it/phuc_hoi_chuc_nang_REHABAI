"""Summarize the predeclared multi-seed Full-v2 vs Optimized-v1 confirmation.

The additional seeds assess optimization variance on the same ten LOSO test
subjects.  They do not turn the post-ablation candidate into an independently
validated production model.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "evaluation"
SEEDS = (42, 7, 2026)
FOLDS = tuple(f"fold_{index:02d}" for index in range(1, 11))
MODELS = ("full_v2", "optimized_v1")
EPSILON = 1e-12

SOURCES = {
    ("full_v2", 42): REPORTS / "loso_ablation_full.json",
    ("optimized_v1", 42): REPORTS / "loso_optimized_v1.json",
    **{
        (model, seed): REPORTS / f"loso_{model}_seed_{seed}.json"
        for model in MODELS
        for seed in (7, 2026)
    },
}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required evaluation report is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of fold results in {path}")
    by_fold = {str(row.get("fold_id")): row for row in payload}
    if len(payload) != 10 or tuple(sorted(by_fold)) != FOLDS:
        raise ValueError(f"Expected exactly {FOLDS}, got {tuple(sorted(by_fold))} in {path}")
    return [by_fold[fold] for fold in FOLDS]


def _describe(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _metric(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    return _describe([float(row[key]) for row in rows])


def _upsert_marked_section(path: Path, section: str, before: str) -> None:
    start = "<!-- MULTISEED_CONFIRMATION_START -->"
    end = "<!-- MULTISEED_CONFIRMATION_END -->"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    block = f"{start}\n{section.rstrip()}\n{end}"
    if start in text and end in text:
        prefix, remainder = text.split(start, 1)
        _, suffix = remainder.split(end, 1)
        updated = prefix.rstrip() + "\n\n" + block + suffix
    elif before in text:
        updated = text.replace(before, block + "\n\n" + before, 1)
    else:
        updated = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(updated, encoding="utf-8")


def main() -> None:
    rows = {key: _read_rows(path) for key, path in SOURCES.items()}

    per_seed: dict[str, Any] = {}
    all_values = {model: {"f1_macro": [], "accuracy": []} for model in MODELS}
    all_deltas: list[float] = []
    seed_mean_deltas: list[float] = []

    for seed in SEEDS:
        seed_key = str(seed)
        per_seed[seed_key] = {"models": {}}
        indexed: dict[str, dict[str, dict[str, Any]]] = {}
        for model in MODELS:
            model_rows = rows[(model, seed)]
            indexed[model] = {row["fold_id"]: row for row in model_rows}
            per_seed[seed_key]["models"][model] = {
                "exercise_macro_f1": _metric(model_rows, "f1_macro"),
                "accuracy": _metric(model_rows, "accuracy"),
            }
            for metric in ("f1_macro", "accuracy"):
                all_values[model][metric].extend(float(row[metric]) for row in model_rows)

        deltas = [
            float(indexed["optimized_v1"][fold]["f1_macro"])
            - float(indexed["full_v2"][fold]["f1_macro"])
            for fold in FOLDS
        ]
        seed_mean_deltas.append(statistics.mean(deltas))
        all_deltas.extend(deltas)
        per_seed[seed_key]["paired_macro_f1"] = {
            "mean_delta": statistics.mean(deltas),
            "median_delta": statistics.median(deltas),
            "wins": sum(delta > EPSILON for delta in deltas),
            "ties": sum(abs(delta) <= EPSILON for delta in deltas),
            "losses": sum(delta < -EPSILON for delta in deltas),
            "per_fold_delta": dict(zip(FOLDS, deltas)),
        }

    aggregate_models = {
        model: {
            "exercise_macro_f1": _describe(all_values[model]["f1_macro"]),
            "accuracy": _describe(all_values[model]["accuracy"]),
        }
        for model in MODELS
    }

    # These are descriptive variance components, not independent-sample tests:
    # each seed reuses the same held-out subject in each fold.
    fold_mean_deltas = [
        statistics.mean(
            float(rows[("optimized_v1", seed)][index]["f1_macro"])
            - float(rows[("full_v2", seed)][index]["f1_macro"])
            for seed in SEEDS
        )
        for index in range(10)
    ]
    within_fold_seed_stds = [
        statistics.stdev(
            float(rows[("optimized_v1", seed)][index]["f1_macro"])
            - float(rows[("full_v2", seed)][index]["f1_macro"])
            for seed in SEEDS
        )
        for index in range(10)
    ]
    wins = sum(delta > EPSILON for delta in all_deltas)
    ties = sum(abs(delta) <= EPSILON for delta in all_deltas)
    losses = sum(delta < -EPSILON for delta in all_deltas)
    stable_direction = all(delta > EPSILON for delta in seed_mean_deltas)
    fold_majority = sum(delta > EPSILON for delta in fold_mean_deltas)

    if stable_direction and wins > losses:
        robustness = "directionally_consistent_across_seeds"
        recommendation = (
            "Optimized-v1 is a promising research candidate, but validate the frozen "
            "architecture on fresh subjects before any production promotion."
        )
    else:
        robustness = "not_stable_across_seeds_and_folds"
        recommendation = (
            "Retain Full-v2 as the reference and prioritize fresh-subject data; do not "
            "promote Optimized-v1."
        )

    result = {
        "protocol": {
            "design": "strict ten-fold subject-wise LOSO",
            "seeds": list(SEEDS),
            "additional_seeds_predeclared": [7, 2026],
            "paired_unit": "identical seed and held-out-subject fold",
            "checkpoint_selection": "validation only",
            "independence_warning": "30 fold-seed rows reuse 10 subjects and are not 30 independent subjects",
            "selection_warning": "Optimized-v1 architecture was selected after seed-42 ablation test inspection",
        },
        "per_seed": per_seed,
        "aggregate_descriptive": {
            "models": aggregate_models,
            "paired_macro_f1": {
                "mean_delta": statistics.mean(all_deltas),
                "median_delta": statistics.median(all_deltas),
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "positive_mean_delta_all_seeds": stable_direction,
                "folds_positive_after_averaging_seeds": fold_majority,
                "folds_total": len(FOLDS),
            },
        },
        "descriptive_variability": {
            "between_subject_std_of_seed_averaged_paired_delta": statistics.stdev(fold_mean_deltas),
            "between_seed_std_of_overall_paired_delta": statistics.stdev(seed_mean_deltas),
            "mean_within_subject_std_across_seeds": statistics.mean(within_fold_seed_stds),
        },
        "robustness_decision": robustness,
        "promotion_allowed": False,
        "production_changed": False,
        "scientific_decision": "E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION",
        "recommendation": recommendation,
    }

    json_path = REPORTS / "multiseed_confirmation_summary.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Multi-seed confirmation: Full v2 vs Optimized-v1",
        "",
        "Protocol: strict 10-fold subject-wise LOSO. Seeds 7 and 2026 were",
        "predeclared confirmations; seed 42 is the original exploratory comparison.",
        "Checkpoints were selected only from validation performance.",
        "",
        "| Seed | Full v2 Macro-F1 | Optimized-v1 Macro-F1 | Paired delta | W/T/L |",
        "|---:|---:|---:|---:|---:|",
    ]
    for seed in SEEDS:
        item = per_seed[str(seed)]
        full = item["models"]["full_v2"]["exercise_macro_f1"]
        optimized = item["models"]["optimized_v1"]["exercise_macro_f1"]
        paired = item["paired_macro_f1"]
        lines.append(
            f"| {seed} | {full['mean']:.4f} +/- {full['std']:.4f} | "
            f"{optimized['mean']:.4f} +/- {optimized['std']:.4f} | "
            f"{paired['mean_delta']:+.4f} | {paired['wins']}/{paired['ties']}/{paired['losses']} |"
        )
    aggregate = result["aggregate_descriptive"]["paired_macro_f1"]
    lines += [
        "",
        "## Aggregate descriptive result",
        "",
        f"Across 30 paired fold-seed evaluations, mean Macro-F1 delta is "
        f"{aggregate['mean_delta']:+.4f}; W/T/L={wins}/{ties}/{losses}.",
        f"The seed-averaged optimized candidate is better on {fold_majority}/10 held-out subjects.",
        "",
        "These 30 rows are repeated evaluations of only 10 subjects, not 30",
        "independent subjects. Multi-seed confirmation measures training randomness;",
        "it cannot repair post-selection bias or establish clinical generalization.",
        "",
        "## Decision",
        "",
        f"Robustness: `{robustness}`.",
        "Production remains unchanged. Final research classification remains",
        "`E_DATASET_TOO_SMALL_OR_INSUFFICIENT_FOR_STRONG_CONCLUSION`.",
        recommendation,
    ]
    markdown = "\n".join(lines) + "\n"
    (REPORTS / "MULTISEED_CONFIRMATION_SUMMARY.md").write_text(markdown, encoding="utf-8")

    optimized_section = "\n".join([
        "## Multi-seed confirmation",
        "",
        f"Additional predeclared seeds 7 and 2026 are complete. Across all three seeds, "
        f"the paired Macro-F1 delta is {aggregate['mean_delta']:+.4f} with "
        f"W/T/L={wins}/{ties}/{losses}. Robustness: `{robustness}`.",
        "",
        "This reuses the same 10 subjects and does not remove post-ablation selection bias.",
        "Production remains unchanged; validation on fresh subjects is required.",
    ])
    _upsert_marked_section(
        REPORTS / "OPTIMIZED_V1_SUMMARY.md", optimized_section, "Production is unchanged."
    )

    compliance_section = "\n".join([
        "## Multi-seed confirmation status",
        "",
        "- Full v2 and Optimized-v1 were evaluated over strict 10-fold LOSO with",
        "  seeds 42, 7 and 2026 (30 paired fold-seed comparisons).",
        f"- Aggregate paired Macro-F1 delta: {aggregate['mean_delta']:+.4f}; "
        f"W/T/L={wins}/{ties}/{losses}; robustness `{robustness}`.",
        "- Production was not changed. The same 10 subjects are reused across seeds,",
        "  so fresh-subject validation remains necessary.",
    ])
    _upsert_marked_section(
        REPORTS / "COMPLIANCE_V3_1_STATUS.md", compliance_section, "## Still environment-dependent"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
