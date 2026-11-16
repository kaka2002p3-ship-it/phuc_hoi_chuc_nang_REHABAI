"""Flag expert-reviewed reps worth a second look; never changes labels."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--reviews',type=Path,required=True); ap.add_argument('--queue',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); args=ap.parse_args()
    r=pd.read_csv(args.reviews,dtype={'video_id':str}); q=pd.read_csv(args.queue,dtype={'video_id':str})
    cols=['video_id','rep_id','exercise','source_video_path','start_frame','end_frame','signal_min','signal_max','signal_range','signal_std','start_time_s','end_time_s','phase_hint','completion_label','review_status','annotator_id','notes']
    df=r.merge(q[[c for c in cols if c in q.columns and c not in ['completion_label','review_status','annotator_id','notes']]],on=['video_id','rep_id'],how='left',suffixes=('','_queue'))
    for c in ['signal_min','signal_max','signal_range','signal_std','start_time_s','end_time_s','start_frame','end_frame']:
        if c in df: df[c]=pd.to_numeric(df[c],errors='coerce')
    reasons=[]
    for ex,g in df.groupby('exercise'):
        # robust quantiles avoid treating naturally different exercises equally
        for idx,row in g.iterrows():
            rr=[]
            if pd.notna(row.signal_range) and row.signal_range <= g.signal_range.quantile(.10): rr.append('biên độ thuộc 10% thấp nhất của bài')
            if pd.notna(row.signal_std) and row.signal_std <= g.signal_std.quantile(.10): rr.append('độ biến thiên rất thấp')
            duration=float(row.end_time_s-row.start_time_s) if pd.notna(row.end_time_s) and pd.notna(row.start_time_s) else np.nan
            if np.isfinite(duration) and (duration < g.assign(duration=g.end_time_s-g.start_time_s).duration.quantile(.10) or duration > g.assign(duration=g.end_time_s-g.start_time_s).duration.quantile(.90)): rr.append('thời lượng nằm ở vùng bất thường')
            if row.completion_label=='uncertain': rr.append('đã được gắn uncertain, cần xem lại')
            if rr: reasons.append((idx,'; '.join(rr)))
    suspect=df.loc[[x[0] for x in reasons]].copy(); suspect['suspicion_reasons']=[x[1] for x in reasons]; suspect['review_again']='pending'; suspect['original_label']=suspect.completion_label
    keep=['video_id','rep_id','exercise','source_video_path','start_frame','end_frame','start_time_s','end_time_s','signal_min','signal_max','signal_range','signal_std','phase_hint','original_label','suspicion_reasons','review_again']
    suspect[keep].to_csv(args.output,index=False,encoding='utf-8-sig'); args.report.parent.mkdir(parents=True,exist_ok=True)
    lines=['# Datanew suspected incorrect review queue','', '- This is a second-review queue only; no labels were changed.', '- `suspicion_reasons` are statistical/quality flags, not proof of incorrect technique.', f'- Total flagged rows: {len(suspect)}', '']
    for ex,g in suspect.groupby('exercise'): lines.append(f'- {ex}: {len(g)} flagged rows, {g.video_id.nunique()} videos; original labels: '+', '.join(f'{k}={v}' for k,v in g.original_label.value_counts().items()))
    args.report.write_text('\n'.join(lines),encoding='utf-8'); print(f'flagged={len(suspect)} output={args.output.resolve()}'); print(suspect.groupby(['exercise','original_label']).size().to_string())
if __name__=='__main__': main()
