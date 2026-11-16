"""Create a human-readable evaluation report without inventing unavailable metrics."""
from __future__ import annotations
import json, statistics
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--source", default="experiments/rehab_ctr_tcn_corrected/loso_results.json")
parser.add_argument("--output", default="reports/evaluation/REHAB_CTR_TCN_EVALUATION_CORRECTED.md")
args = parser.parse_args()
source = ROOT / args.source
output = ROOT / args.output
data = json.loads(source.read_text(encoding="utf-8"))
lines = ["# RehabCTR-TCN evaluation", "", "Protocol: subject-wise LOSO on verified real landmark data.", "", "| Exercise | Valid folds | Skipped folds | Accuracy | Macro Precision | Macro Recall | Macro-F1 | Majority F1 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
for exercise in ["HAND_OPENING", "ELBOW_EXTENSION"]:
    rows = [row for row in data["results"] if row["exercise"] == exercise]
    done = [row for row in rows if row["status"] == "complete"]
    accuracy = statistics.mean(row["metrics"]["accuracy"] for row in done) if done else float("nan")
    precision = statistics.mean(row["metrics"]["precision_macro"] for row in done) if done else float("nan")
    recall = statistics.mean(row["metrics"]["recall_macro"] for row in done) if done else float("nan")
    f1 = statistics.mean(row["metrics"]["f1_macro"] for row in done) if done else float("nan")
    majority = statistics.mean(row["metrics"].get("majority_baseline_f1_macro", float("nan")) for row in done) if done else float("nan")
    lines.append(f"| {exercise} | {len(done)} | {len(rows)-len(done)} | {accuracy:.4f} | {precision:.4f} | {recall:.4f} | {f1:.4f} | {majority:.4f} |")
lines += ["", "## Interpretation", "", "The model was trained with Joint/Bone/Motion streams, graph encoders, MS-TCN refinement, attention pooling and a binary correctness head.", "", "Rep MAE, exact count accuracy, boundary F1 and temporal IoU are **not available** because the verified manifests contain video-level Complete/Incomplete labels but no repetition boundaries or rep-level labels. No pseudo-labels were used.", "", "A fold is skipped when its target exercise has no test samples or only one test class; this is required for a valid binary LOSO estimate.", "", "The current result is a research baseline for correctness classification, not a clinical or product-ready rep counter.", ""]
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(lines), encoding="utf-8")
print(output)
