"""Validate human-reviewed datanew labels before supervised training."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--reviews',type=Path,required=True); ap.add_argument('--queue',type=Path,required=True); args=ap.parse_args()
    if not args.reviews.is_file(): raise SystemExit(f'BLOCKED: review file does not exist: {args.reviews}')
    reviews=pd.read_csv(args.reviews,dtype={'video_id':str}); queue=pd.read_csv(args.queue,dtype={'video_id':str})
    required={'video_id','rep_id','completion_label','review_status','annotator_id','start_frame','end_frame'}
    missing=required-set(reviews.columns)
    if missing: raise SystemExit(f'BLOCKED: missing columns: {sorted(missing)}')
    errors=[]
    if reviews.duplicated(['video_id','rep_id']).any(): errors.append('duplicate video_id/rep_id')
    if (~reviews.completion_label.isin(['correct','incorrect','uncertain'])).any(): errors.append('invalid completion_label')
    if (reviews.end_frame<=reviews.start_frame).any(): errors.append('end_frame <= start_frame')
    if reviews.annotator_id.fillna('').str.strip().eq('').any(): errors.append('missing annotator_id')
    known=set(map(tuple,queue[['video_id','rep_id']].to_records(index=False))); found=set(map(tuple,reviews[['video_id','rep_id']].to_records(index=False)))
    if found-known: errors.append(f'{len(found-known)} rows not found in queue')
    if errors: raise SystemExit('BLOCKED: '+'; '.join(errors))
    confirmed=reviews[reviews.completion_label.isin(['correct','incorrect'])]
    print(f'PASS rows={len(reviews)} confirmed={len(confirmed)} uncertain={len(reviews)-len(confirmed)}')
    if len(confirmed): print(confirmed.groupby(['exercise','completion_label']).size().to_string())
if __name__=='__main__': main()
