from __future__ import annotations
import json, statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run_dir = root / "experiments/teacher_student_v1/runs"
rows=[]
for p in sorted(run_dir.glob("fold_*_rehab_motionnet_summary.json")):
    d=json.loads(p.read_text(encoding="utf-8")); h=d.get("history",[])
    if not h: continue
    best=max(h,key=lambda x: x.get("val_f1",0))
    rows.append({"fold_id":d.get("fold_id"),"best_val_f1":best.get("val_f1"),"best_epoch":best.get("epoch"),"teacher_student":best.get("teacher_student"),"pseudo_label_acceptance":best.get("pseudo_label_acceptance")})
out={"experiment":"teacher_student_v1","completed_folds":len(rows),"folds":rows}
if rows:
    vals=[r["best_val_f1"] for r in rows]
    out["best_val_f1_mean"]=statistics.mean(vals); out["best_val_f1_std"]=statistics.stdev(vals) if len(vals)>1 else 0.0
(root/"experiments/teacher_student_v1/summary.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
