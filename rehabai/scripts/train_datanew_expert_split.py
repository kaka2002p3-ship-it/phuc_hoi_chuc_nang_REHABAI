"""Train/evaluate expert rep labels using precomputed video-disjoint manifests."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, classification_report
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES=['signal_min','signal_max','signal_range','signal_std','start_time_s','end_time_s']

def read_manifest(path, queue):
    df=pd.read_csv(path,dtype={'video_id':str})
    df=df[df.completion_label.isin(['correct','incorrect'])].copy()
    missing=[c for c in FEATURES if c not in df.columns]
    if missing:
        q=pd.read_csv(queue,dtype={'video_id':str})
        df=df.merge(q[['video_id','rep_id']+FEATURES],on=['video_id','rep_id'],how='left',validate='one_to_one')
    missing=[c for c in FEATURES if c not in df.columns or df[c].isna().any()]
    if missing: raise SystemExit(f'BLOCKED {path}: missing feature values {missing}')
    df['target']=df.completion_label.map({'incorrect':0,'correct':1}).astype(int)
    return df

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--split-dir',type=Path,required=True); ap.add_argument('--queue',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--epochs',type=int,default=30); args=ap.parse_args()
    np.random.seed(args.seed); args.output.mkdir(parents=True,exist_ok=True)
    train=read_manifest(args.split_dir/'train_manifest.csv',args.queue); val=read_manifest(args.split_dir/'val_manifest.csv',args.queue); test=read_manifest(args.split_dir/'test_manifest.csv',args.queue)
    results=[]
    for ex in sorted(set(train.exercise)|set(val.exercise)|set(test.exercise)):
        tr,va,te=[x[x.exercise.eq(ex)].copy() for x in (train,val,test)]
        if tr.empty: continue
        model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=max(100,args.epochs*10),class_weight='balanced',random_state=args.seed))
        model.fit(tr[FEATURES],tr.target)
        item={'exercise':ex,'train':{'rows':len(tr),'videos':tr.video_id.nunique(),'correct':int((tr.target==1).sum()),'incorrect':int((tr.target==0).sum())},'val':{'rows':len(va),'videos':va.video_id.nunique(),'classes':sorted(va.target.unique().tolist())},'test':{'rows':len(te),'videos':te.video_id.nunique(),'classes':sorted(te.target.unique().tolist())}}
        for name,part in [('val',va),('test',te)]:
            if part.empty: item[name]['status']='empty'; continue
            pred=model.predict(part[FEATURES]); item[name].update({'status':'evaluated','accuracy':float(accuracy_score(part.target,pred)),'f1_macro':float(f1_score(part.target,pred,average='macro',zero_division=0)),'confusion_matrix':confusion_matrix(part.target,pred,labels=[0,1]).tolist(),'report':classification_report(part.target,pred,labels=[0,1],target_names=['incorrect','correct'],output_dict=True,zero_division=0)})
        results.append(item); print(f'[{ex}] train={len(tr)} val={len(va)} test={len(te)} test_f1={item["test"].get("f1_macro","NA")}',flush=True)
    annotators=sorted(set(pd.concat([train, val, test]).annotator_id.dropna().astype(str))) if 'annotator_id' in train else []
    payload={'status':'complete','protocol':'fixed video-disjoint train/val/test','seed':args.seed,'epochs_argument':args.epochs,'label_source':'expert_reviewed','annotators':annotators,'features':FEATURES,'class_weight':'balanced','results':results,'warning':'Research baseline using summary kinematics; do not promote without stronger video/subject generalization.'}
    (args.output/'metrics.json').write_text(json.dumps(payload,indent=2),encoding='utf-8'); print(json.dumps({'status':'complete','output':str((args.output/'metrics.json').resolve())},indent=2),flush=True)
if __name__=='__main__': main()
