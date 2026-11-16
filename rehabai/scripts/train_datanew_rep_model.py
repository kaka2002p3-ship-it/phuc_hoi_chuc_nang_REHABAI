"""Research-only rep-level baseline for the experimental datanew labels.

Uses kinematic summary columns already present in the review queue. This is not
a clinical model: auto_rule_v1 labels are derived from signal range, so metrics
must not be interpreted as real correctness performance.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES=['signal_min','signal_max','signal_range','signal_std','start_time_s','end_time_s']
NON_LEAKY_FEATURES=['signal_min','signal_max','signal_std','start_time_s','end_time_s']
STRICT_FEATURES=['start_time_s','end_time_s']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--labels',type=Path,required=True); ap.add_argument('--epochs',type=int,default=30); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--output',type=Path,default=Path('experiments/datanew_rep_model')); ap.add_argument('--no-leakage',action='store_true'); ap.add_argument('--strict-no-leakage',action='store_true'); ap.add_argument('--expert-mode',action='store_true',help='Use expert-reviewed labels and all confirmed rows; class-balanced logistic baseline'); args=ap.parse_args()
    np.random.seed(args.seed); df=pd.read_csv(args.labels)
    print(f'load rows={len(df)} labels={args.labels}',flush=True)
    df=df[df.completion_label.isin(['correct','incorrect'])].copy()
    df['target']=df.completion_label.map({'incorrect':0,'correct':1}).astype(int)
    missing_features=[c for c in FEATURES if c not in df.columns]
    if missing_features and args.expert_mode:
        queue=args.labels.parent/'datanew_rep_review_queue.csv'
        if not queue.is_file(): raise SystemExit(f'BLOCKED missing features and queue not found: {queue}')
        evidence=pd.read_csv(queue,dtype={'video_id':str})
        df=df.merge(evidence[['video_id','rep_id']+FEATURES],on=['video_id','rep_id'],how='left',validate='one_to_one')
        print(f'joined features from {queue}',flush=True)
    missing=[c for c in FEATURES if c not in df.columns]
    if missing: raise SystemExit(f'BLOCKED missing feature columns: {missing}')
    # Expert labels are independent of the kinematic statistics, so use the
    # full evidence feature set in expert mode. Strict timing-only mode remains
    # available for the old heuristic-label smoke tests.
    active_features=FEATURES if args.expert_mode else (STRICT_FEATURES if args.strict_no_leakage else (NON_LEAKY_FEATURES if args.no_leakage else FEATURES))
    df=df.dropna(subset=active_features+['video_id','exercise'])
    if df.empty: raise SystemExit('BLOCKED no confirmed labels')
    args.output.mkdir(parents=True,exist_ok=True); results=[]
    for exercise,part in df.groupby('exercise',sort=True):
        if part.target.nunique()<2 or part.video_id.nunique()<2:
            print(f'[{exercise}] SKIP insufficient classes/groups',flush=True); continue
        splitter=GroupShuffleSplit(n_splits=100,test_size=.25,random_state=args.seed)
        split=None
        for train_idx,test_idx in splitter.split(part[active_features],part.target,groups=part.video_id):
            if part.iloc[train_idx].target.nunique()==2 and part.iloc[test_idx].target.nunique()==2:
                split=(train_idx,test_idx); break
        if split is None:
            print(f'[{exercise}] SKIP no video-disjoint split contains both classes in train and test',flush=True)
            results.append({'exercise':exercise,'status':'skipped_no_valid_video_split','rows':len(part),'videos':int(part.video_id.nunique()),'incorrect_rows':int((part.target==0).sum()),'incorrect_videos':int(part.loc[part.target.eq(0),'video_id'].nunique())})
            continue
        train_idx,test_idx=split
        xtr,xte=part.iloc[train_idx][active_features],part.iloc[test_idx][active_features]; ytr,yte=part.iloc[train_idx].target,part.iloc[test_idx].target
        model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=max(100,args.epochs*10),random_state=args.seed,class_weight='balanced'))
        model.fit(xtr,ytr); pred=model.predict(xte)
        metrics={'exercise':exercise,'status':'complete','train_rows':len(train_idx),'test_rows':len(test_idx),'train_videos':int(part.iloc[train_idx].video_id.nunique()),'test_videos':int(part.iloc[test_idx].video_id.nunique()),'accuracy':float(accuracy_score(yte,pred)),'f1_macro':float(f1_score(yte,pred,average='macro',zero_division=0)),'report':classification_report(yte,pred,output_dict=True,zero_division=0)}
        results.append(metrics); print(f'[{exercise}] train={len(train_idx)} test={len(test_idx)} videos={metrics["test_videos"]} f1_macro={metrics["f1_macro"]:.4f} accuracy={metrics["accuracy"]:.4f}',flush=True)
    payload={'protocol':'group split by video_id','seed':args.seed,'epochs_argument':args.epochs,'label_source':'expert_reviewed_PT_01' if args.expert_mode else 'auto_rule_v1 experimental','features':active_features,'no_leakage':args.no_leakage or args.strict_no_leakage,'expert_mode':args.expert_mode,'class_weight':'balanced','warning':'Expert labels are single-annotator and imbalanced; metrics are research-only until multi-annotator/fresh-subject validation.','results':results}
    (args.output/'metrics.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    (args.output/'README.md').write_text('# Datanew rep model (research only)\n\nMetrics are measured against auto_rule_v1 heuristic labels and must not be interpreted as clinical correctness.\n',encoding='utf-8')
    print(json.dumps({'status':'complete','output':str((args.output/'metrics.json').resolve()),'completed_exercises':sum(r.get('status')=='complete' for r in results),'skipped_exercises':sum(r.get('status')!='complete' for r in results)},indent=2),flush=True)
if __name__=='__main__': main()
