"""Create leakage-safe train/val/test manifests from expert rep labels.

Groups are videos. Incorrect-containing videos are distributed where possible;
if an exercise has too few incorrect videos, the split is marked single-class
and must not be used for a binary correctness claim.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def allocate_videos(g, seed):
    videos=g[['video_id']].drop_duplicates().sample(frac=1,random_state=seed).video_id.tolist()
    bad=g[g.completion_label.eq('incorrect')].groupby('video_id').size().sort_values(ascending=False).index.tolist()
    good=[v for v in videos if v not in bad]
    # Target proportions, while reserving incorrect videos for train/val/test
    # whenever at least three independent incorrect videos exist.
    if len(bad)>=3:
        n_test=max(1,round(len(bad)*.15)); n_val=max(1,round(len(bad)*.15))
        split_bad={'test':bad[:n_test],'val':bad[n_test:n_test+n_val], 'train':bad[n_test+n_val:]}
    elif len(bad)==2:
        split_bad={'train':bad[:1],'val':[], 'test':bad[1:]}
    elif len(bad)==1:
        split_bad={'train':bad,'val':[], 'test':[]}
    else:
        split_bad={'train':[],'val':[],'test':[]}
    n=len(good); n_test=max(1,round(n*.15)); n_val=max(1,round(n*.15))
    split_good={'test':good[:n_test],'val':good[n_test:n_test+n_val],'train':good[n_test+n_val:]}
    return {k:split_bad[k]+split_good[k] for k in ('train','val','test')}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); ap.add_argument('--seed',type=int,default=42); args=ap.parse_args()
    df=pd.read_csv(args.input,dtype={'video_id':str}); df=df[df.completion_label.isin(['correct','incorrect'])].copy()
    rows=[]; report=[]
    for i,(ex,g) in enumerate(df.groupby('exercise',sort=True)):
        groups=allocate_videos(g,args.seed+i)
        for split,vids in groups.items():
            part=g[g.video_id.isin(vids)].copy(); part['split']=split; rows.append(part)
            report.append({'exercise':ex,'split':split,'rows':len(part),'videos':part.video_id.nunique(),'correct':int((part.completion_label=='correct').sum()),'incorrect':int((part.completion_label=='incorrect').sum())})
    out=pd.concat(rows,ignore_index=True); args.output_dir.mkdir(parents=True,exist_ok=True)
    for split in ('train','val','test'):
        out[out.split.eq(split)].to_csv(args.output_dir/f'{split}_manifest.csv',index=False,encoding='utf-8-sig')
    summary=pd.DataFrame(report); args.report.parent.mkdir(parents=True,exist_ok=True)
    lines=['# Datanew expert video-group split','', '- Group key: `video_id`; no video appears in more than one split.', '- Only expert-confirmed `correct/incorrect` labels are included.', '- `uncertain` rows are excluded.', '', '## Split summary']
    lines += [f"- {r.exercise} / {r.split}: rows={r.rows}, videos={r.videos}, correct={r.correct}, incorrect={r.incorrect}" for r in summary.itertuples()]
    lines += ['', '## Warnings']
    for ex,g in df.groupby('exercise'):
        bad_v=g.loc[g.completion_label.eq('incorrect'),'video_id'].nunique()
        if bad_v<3: lines.append(f'- {ex}: only {bad_v} video(s) contain incorrect labels; val/test may be single-class or empty for incorrect. Do not report binary generalization F1.')
    args.report.write_text('\n'.join(lines),encoding='utf-8'); print(summary.to_string(index=False)); print(f'output={args.output_dir.resolve()}')
if __name__=='__main__': main()
