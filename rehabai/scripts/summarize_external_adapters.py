"""Summarize frozen-external adapter LOSO experiments without auto-promotion."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "evaluation"
SOURCES = {
    "rehab24_adapter": ("Frozen REHAB24-6 encoder + adapter", "loso_external_adapter_rehab24.json"),
    "mobiphysio_adapter": ("Frozen MobiPhysio encoder + adapter", "loso_external_adapter_mobiphysio.json"),
    "combined_adapter": ("Frozen 02+03 encoder + adapter", "loso_external_adapter_combined.json"),
    "v2": ("Existing RehabMotionNet v2", "loso_upper_limb_v2.json"),
    "ensemble": ("Existing validation-selected ensemble", "loso_ensemble_v1.json"),
}


def metric(rows: list[dict], name: str) -> dict | None:
    values = [float(row[name]) for row in rows if row.get(name) is not None]
    if not values:
        return None
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    loaded = {}
    for key, (label, filename) in SOURCES.items():
        path = REPORTS / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        # Per-model evaluator reports are row arrays. The ensemble evaluator
        # keeps its rows under ``folds`` and uses explicit test metric names.
        if key == "ensemble":
            if not isinstance(payload, dict) or not isinstance(payload.get("folds"), list):
                raise ValueError(f"{filename} does not contain ensemble folds")
            rows = [
                {
                    **row,
                    "f1_macro": row["test_f1_macro"],
                    "accuracy": row["test_accuracy"],
                }
                for row in payload["folds"]
            ]
        else:
            if not isinstance(payload, list):
                raise ValueError(f"{filename} is not a per-fold row array")
            rows = payload
        by_fold = {str(row["fold_id"]): row for row in rows}
        if set(by_fold) != {f"fold_{index:02d}" for index in range(1, 11)}:
            raise ValueError(f"{filename} is not a complete strict ten-fold report")
        loaded[key] = {"label": label, "rows": by_fold}

    models = {}
    for key, item in loaded.items():
        rows = list(item["rows"].values())
        models[key] = {
            "label": item["label"],
            "exercise_macro_f1": metric(rows, "f1_macro"),
            "accuracy": metric(rows, "accuracy"),
            "weighted_f1": metric(rows, "f1_weighted"),
            "completion_macro_f1": metric(rows, "completion_f1_macro"),
            "completion_accuracy": metric(rows, "completion_accuracy"),
        }

    paired = {}
    baseline = loaded["ensemble"]["rows"]
    for key in ("rehab24_adapter", "mobiphysio_adapter", "combined_adapter"):
        deltas = [
            float(loaded[key]["rows"][fold]["f1_macro"]) - float(baseline[fold]["f1_macro"])
            for fold in sorted(baseline)
        ]
        paired[key] = {
            "mean_f1_delta_vs_ensemble": statistics.mean(deltas),
            "fold_wins": sum(delta > 0 for delta in deltas),
            "fold_ties": sum(delta == 0 for delta in deltas),
            "fold_losses": sum(delta < 0 for delta in deltas),
            "per_fold_delta": dict(zip(sorted(baseline), deltas)),
        }

    best_key = max(
        ("rehab24_adapter", "mobiphysio_adapter", "combined_adapter"),
        key=lambda key: models[key]["exercise_macro_f1"]["mean"],
    )
    beats_existing = (
        models[best_key]["exercise_macro_f1"]["mean"] > models["ensemble"]["exercise_macro_f1"]["mean"]
        and models[best_key]["accuracy"]["mean"] >= models["v2"]["accuracy"]["mean"]
        and paired[best_key]["fold_wins"] >= 6
    )
    result = {
        "protocol": "exploratory paired strict ten-fold subject-wise LOSO",
        "models": models,
        "paired_vs_ensemble": paired,
        "best_adapter_by_mean_macro_f1": best_key,
        "passes_predeclared_research_gate": beats_existing,
        "production_changed": False,
        "recommendation": (
            "validate_best_adapter_on_fresh_subjects_before_any_promotion"
            if beats_existing
            else "keep_existing_model; do_not_promote_external_adapter"
        ),
        "selection_note": "Three adapter sources shared the LOSO test protocol; selecting the best is exploratory and requires independent confirmation.",
    }
    (REPORTS / "external_adapter_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    lines = [
        "# Frozen external-encoder adapter summary",
        "",
        "All figures use strict ten-fold subject-wise LOSO on data 01. Because three adapter",
        "sources share the test folds, selecting the best result is exploratory only.",
        "",
        "| Model | Exercise Macro-F1 | Accuracy | Completion Macro-F1 | Wins vs ensemble |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, item in models.items():
        completion = item["completion_macro_f1"]
        completion_text = f"{completion['mean']:.4f}" if completion else "n/a"
        wins = str(paired[key]["fold_wins"]) if key in paired else "n/a"
        lines.append(
            f"| {item['label']} | {item['exercise_macro_f1']['mean']:.4f} | "
            f"{item['accuracy']['mean']:.4f} | {completion_text} | {wins} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        f"Best adapter: `{best_key}`.",
        f"Research gate passed: `{str(beats_existing).lower()}`.",
        "Production remains unchanged. Any promotion requires confirmation on fresh subjects",
        "or a new evaluation protocol that was not used to select among these variants.",
    ]
    (REPORTS / "EXTERNAL_ADAPTER_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
