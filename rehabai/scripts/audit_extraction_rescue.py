"""Rank failed extractions for manual/re-extraction review without relaxing gates."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"data/stage3_real/indexes/extraction_quality.csv"
output=ROOT/"reports/evaluation/extraction_rescue_candidates.csv"
table=pd.read_csv(source)
failed=table[table.status!="success"].copy()
# Near-gate candidates are useful for inspection, but remain rejected until a
# new reviewed extractor/gate version validates them.
failed["rescue_priority"]=(failed.pose_missing_rate.fillna(1.0)*1000-failed.frames.fillna(0)/10000)
failed=failed.sort_values(["rescue_priority","exercise_id","subject_id"])
failed.to_csv(output,index=False,encoding="utf-8-sig")
summary=failed.groupby(["exercise_id","status"]).size().rename("count").reset_index()
print(summary.to_string(index=False)); print(f"candidate_file={output} rows={len(failed)}")
