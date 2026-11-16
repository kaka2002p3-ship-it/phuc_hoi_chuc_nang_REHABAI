"""Merge a complete second-review subset into a new expert-label artifact."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',type=Path,required=True); ap.add_argument('--second-review',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    keys=['video_id','rep_id']; base=pd.read_csv(args.base,dtype={'video_id':str}); review=pd.read_csv(args.second_review,dtype={'video_id':str})
    if review.duplicated(keys).any(): raise SystemExit('BLOCKED duplicate keys in second review')
    known=set(map(tuple,base[keys].to_records(index=False))); incoming=set(map(tuple,review[keys].to_records(index=False)))
    if incoming-known: raise SystemExit(f'BLOCKED {len(incoming-known)} unknown keys')
    out=base.set_index(keys); update=review.set_index(keys)
    columns=['completion_label','review_status','annotator_id','notes','reviewed_at','start_frame','end_frame']
    for col in columns: out.loc[update.index,col]=update[col]
    out=out.reset_index(); args.output.parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    print(f'rows={len(out)} updated={len(update)} output={args.output.resolve()}'); print(out.groupby(['exercise','completion_label']).size().to_string())
if __name__=='__main__': main()
