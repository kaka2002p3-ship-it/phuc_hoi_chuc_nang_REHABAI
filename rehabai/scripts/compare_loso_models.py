from __future__ import annotations

import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
v2 = json.loads((root / "reports/evaluation/loso_upper_limb_v2.json").read_text(encoding="utf-8"))
ctr = json.loads((root / "reports/evaluation/loso_ctr_gcn_v1.json").read_text(encoding="utf-8"))
by_v2 = {x["fold_id"]: x for x in v2}
by_ctr = {x["fold_id"]: x for x in ctr}
rows = []
for fold in sorted(by_v2):
    old, new = by_v2[fold], by_ctr[fold]
    rows.append({
        "fold_id": fold,
        "v2_f1_macro": old["f1_macro"],
        "ctr_gcn_f1_macro": new["f1_macro"],
        "delta_f1_macro": new["f1_macro"] - old["f1_macro"],
        "v2_accuracy": old["accuracy"],
        "ctr_gcn_accuracy": new["accuracy"],
    })
deltas = [row["delta_f1_macro"] for row in rows]
out = {
    "comparison": "strict paired 10-fold LOSO",
    "folds": rows,
    "mean_delta_f1_macro": statistics.mean(deltas),
    "median_delta_f1_macro": statistics.median(deltas),
    "ctr_better_folds": sum(x > 0 for x in deltas),
    "v2_better_folds": sum(x < 0 for x in deltas),
    "recommendation": "promote_ctr_gcn_for_exercise_experimental_only" if statistics.mean(deltas) > 0 else "keep_v2",
}
(root / "reports/evaluation/ctr_gcn_vs_v2.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
(root / "research/tables/proposed_comparison.csv").write_text(
    "model,protocol,samples,exercise_macro_f1,exercise_accuracy,completion_macro_f1,completion_accuracy\n"
    "RehabMotionNet_upper_limb_v2,10-fold_subject-wise_LOSO,387,0.3544,0.4379,0.4828,0.5024\n"
    "UpperLimbCTRGCN_v1,10-fold_subject-wise_LOSO,387,0.3648,0.4335,0.5237,0.5601\n",
    encoding="utf-8",
)
print(json.dumps(out, indent=2))
