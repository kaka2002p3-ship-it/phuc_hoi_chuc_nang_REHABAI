"""Validate reviewed rep-level annotations before segmentation/count training."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("manifest"); args=parser.parse_args()
    table=pd.read_csv(args.manifest,dtype={"subject_id":str})
    reviewed=table[table.review_status.astype(str).str.lower()=="approved"].copy()
    errors=[]
    for index,row in reviewed.iterrows():
        if pd.isna(row.rep_id) or pd.isna(row.start_frame) or pd.isna(row.end_frame): errors.append(f"row {index+2}: missing boundary/rep_id"); continue
        if int(row.start_frame)<0 or int(row.end_frame)<=int(row.start_frame): errors.append(f"row {index+2}: invalid frame range")
        if str(row.completion_label).lower() not in {"complete","incomplete","0","1","0.0","1.0"}: errors.append(f"row {index+2}: invalid completion label")
    duplicates=reviewed.duplicated(["video_id","rep_id"]).sum()
    if duplicates: errors.append(f"duplicate (video_id, rep_id): {duplicates}")
    print(f"rows={len(table)} approved={len(reviewed)} errors={len(errors)}")
    for error in errors: print(f"ERROR {error}")
    raise SystemExit(1 if errors else 0)
if __name__=="__main__": main()
