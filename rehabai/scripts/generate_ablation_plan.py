"""Generate reproducible, test-subject-safe ablation commands."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "experiments/upper_limb_v1"
out = base / "ablation_plan.json"
variants = ["full", "minus_hand", "minus_kinematic", "minus_contrastive", "minus_mstcn", "minus_attention"]
rows = []
for v in variants:
    args = [] if v == "full" else [f"--no_{v.removeprefix('minus_')}" ]
    rows.append({"variant": v, "args": args, "folds": 10, "selection": "validation_macro_f1", "test_used_for_selection": False})
out.write_text(json.dumps({"protocol": "upper_limb_v2_ablation", "variants": rows}, indent=2), encoding="utf-8")
print(out)
