"""Create a deterministic, row-balanced training manifest without fabrication.

All incorrect rows are retained; correct rows are sampled without replacement.
Uncertain rows are excluded. This is a training manifest, not an evaluation
split. Group/subject constraints must be audited separately.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); ap.add_argument('--queue',type=Path,default=None,help='Original queue containing kinematic feature columns'); ap.add_argument('--seed',type=int,default=42); args=ap.parse_args()
    df=pd.read_csv(args.input,dtype={'video_id':str}); df=df[df.completion_label.isin(['correct','incorrect'])].copy()
    if args.queue:
        queue=pd.read_csv(args.queue,dtype={'video_id':str})
        feature_cols=[c for c in ['signal_min','signal_max','signal_range','signal_std','start_time_s','end_time_s','phase_hint','evidence'] if c in queue.columns]
        join_cols=['video_id','rep_id']
        df=df.drop(columns=[c for c in feature_cols if c in df.columns],errors='ignore').merge(queue[join_cols+feature_cols],on=join_cols,how='left',validate='one_to_one')
    parts=[]; report=[]
    for exercise,g in df.groupby('exercise',sort=True):
        bad=g[g.completion_label.eq('incorrect')]
        good=g[g.completion_label.eq('correct')]
        if bad.empty: raise SystemExit(f'BLOCKED {exercise}: no incorrect rows')
        sampled=good.sample(n=min(len(good),len(bad)),random_state=args.seed)
        part=pd.concat([bad,sampled],ignore_index=True).sample(frac=1,random_state=args.seed).reset_index(drop=True)
        parts.append(part)
        report.append({'exercise':exercise,'incorrect_kept':len(bad),'correct_sampled':len(sampled),'videos_total':g.video_id.nunique(),'incorrect_videos':bad.video_id.nunique(),'source_groups':','.join(sorted(g.source_group.unique())) if 'source_group' in g else ''})
    out=pd.concat(parts,ignore_index=True); args.output.parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    summary=pd.DataFrame(report); lines=['# Expert-label balanced training manifest','', '- Only expert-confirmed `correct/incorrect` rows are included.', '- All `incorrect` rows are retained.', '- `correct` rows are sampled without replacement; no synthetic labels or duplicate rows are created.', '- This file is for training only; it is not a valid subject-wise test split.', '', '## Summary']
    lines += [f"- {r.exercise}: incorrect={r.incorrect_kept}, correct={r.correct_sampled}, total={r.incorrect_kept+r.correct_sampled}, incorrect_videos={r.incorrect_videos}" for r in summary.itertuples()]
    lines += ['', '## Critical limitation', '- HAND_OPENING has only one video containing incorrect reps. A video-disjoint test set cannot contain both classes until more incorrect videos are labeled.', '- ELBOW_FLEXION has incorrect reps in four videos, all from source ex1; source groups are not confirmed subjects.']
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text('\n'.join(lines),encoding='utf-8'); print(f'rows={len(out)} output={args.output.resolve()}'); print(summary.to_string(index=False))
if __name__=='__main__': main()
