"""Build a conservative rep-level review queue from already extracted datanew NPZs.

This tool detects candidate movement cycles and computes kinematic evidence. It never
turns a heuristic into a clinical correct/incorrect label: every row starts as
``uncertain`` and requires review.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def _angle(a, b, c):
    v1, v2 = a-b, c-b
    den=np.linalg.norm(v1,axis=1)*np.linalg.norm(v2,axis=1)
    return np.degrees(np.arccos(np.clip(np.sum(v1*v2,axis=1)/(den+1e-8),-1,1)))

def _signal(data, exercise):
    pose=data['pose_landmarks'][...,:3]
    if exercise == 'ELBOW_FLEXION':
        vals=[]
        for side in ((11,13,15),(12,14,16)):
            vals.append(_angle(pose[:,side[0]],pose[:,side[1]],pose[:,side[2]]))
        x=np.nan_to_num(np.stack(vals),nan=180.0)
        return x[np.argmax(np.ptp(x,axis=1))]
    hands=[]
    for key in ('left_hand_landmarks','right_hand_landmarks'):
        h=data[key][...,:3]; width=np.linalg.norm(h[:,5]-h[:,17],axis=1)+1e-8
        tips=h[:,[4,8,12,16,20]]
        hands.append(np.mean(np.linalg.norm(tips-h[:,0,None],axis=2),axis=1)/width)
    x=np.nan_to_num(np.stack(hands),nan=0.0)
    return x[np.argmax(np.ptp(x,axis=1))]

def _peaks(x, min_gap=8):
    # local extrema with non-maximum suppression; enough for review, not a labeler.
    scale=max(float(np.ptp(x)),1e-6); candidates=[]
    for i in range(1,len(x)-1):
        if (x[i]>=x[i-1] and x[i]>x[i+1]) or (x[i]<=x[i-1] and x[i]<x[i+1]):
            candidates.append(i)
    chosen=[]
    for i in sorted(candidates,key=lambda j: abs(x[j]-np.median(x)),reverse=True):
        if all(abs(i-j)>=min_gap for j in chosen): chosen.append(i)
    return sorted(chosen)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--catalog',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); args=ap.parse_args()
    cat=pd.read_csv(args.catalog); rows=[]; videos=0
    for rec in cat[cat.status.eq('ready')].to_dict('records'):
        out=Path(str(rec['output']))
        if not out.is_file(): continue
        videos+=1
        with np.load(out,allow_pickle=False) as d: x=_signal(d,rec['exercise']); timestamps=d['timestamps'] if 'timestamps' in d else np.arange(len(x))/30
        # The extractor stores timestamps in milliseconds; expose seconds to reviewers.
        timestamps=np.asarray(timestamps,float)
        if len(timestamps) and float(np.nanmax(timestamps)) > 100: timestamps=timestamps/1000.0
        x=np.asarray(x,float); rng=float(np.ptp(x)); sd=float(np.std(x)); peaks=_peaks(x)
        # A cycle is a pair of alternating extrema; retain only meaningful excursions.
        boundaries=[0]+peaks+[len(x)-1]; rep=0
        for a,b in zip(boundaries,boundaries[1:]):
            if b-a<8 or float(np.ptp(x[a:b+1])) < max(rng*.12, 1e-4): continue
            rep+=1; seg=x[a:b+1]; direction='flexion' if float(np.mean(np.diff(seg)))<0 else 'opening'
            rows.append({'video_id':rec['sample_id'],'source_video_path':rec['file'],'exercise':rec['exercise'],'rep_id':rep,'start_frame':int(a),'end_frame':int(b),'start_time_s':float(timestamps[a]),'end_time_s':float(timestamps[b]),'signal_min':float(np.min(seg)),'signal_max':float(np.max(seg)),'signal_range':float(np.ptp(seg)),'signal_std':float(np.std(seg)),'phase_hint':direction,'suggested_label':'uncertain','review_status':'pending','evidence':'kinematic cycle candidate; human review required'})
        if rep==0:
            rows.append({'video_id':rec['sample_id'],'source_video_path':rec['file'],'exercise':rec['exercise'],'rep_id':1,'start_frame':0,'end_frame':len(x)-1,'start_time_s':float(timestamps[0]),'end_time_s':float(timestamps[-1]),'signal_min':float(np.min(x)),'signal_max':float(np.max(x)),'signal_range':rng,'signal_std':sd,'phase_hint':'no_clear_cycle','suggested_label':'uncertain','review_status':'pending','evidence':'no clear cycle; review full clip'})
    out=pd.DataFrame(rows); args.output.parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    args.report.parent.mkdir(parents=True,exist_ok=True); summary=out.groupby(['exercise','suggested_label']).size().rename('count').reset_index() if len(out) else pd.DataFrame()
    counts='\n'.join(f'- {r.exercise} / {r.suggested_label}: {r.count}' for r in summary.itertuples()) if len(summary) else 'No rows generated.'
    lines=['# Datanew rep review queue','',f'- Ready videos scanned: {videos}',f'- Candidate rep rows: {len(out)}','- All suggestions are `uncertain`; no correctness labels were fabricated.','', '## Counts', counts,'', 'Review `start_frame`, `end_frame`, video evidence, then fill `correct/incorrect` in a separate reviewed manifest.']
    args.report.write_text('\n'.join(lines),encoding='utf-8'); print(f'videos={videos} candidate_reps={len(out)} output={args.output.resolve()} report={args.report.resolve()}')
if __name__=='__main__': main()
