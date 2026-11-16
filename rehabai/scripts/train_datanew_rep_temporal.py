"""Train exercise-specific 3-stream CTR-GCN/MS-TCN on expert rep windows."""
from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from sklearn.metrics import accuracy_score,confusion_matrix,f1_score,classification_report
from torch.utils.data import DataLoader,WeightedRandomSampler
from training.datanew_rep_dataset import DatanewRepDataset
from training.models.rehab_ctr_tcn import RehabCTRTCN

def seed_all(v): random.seed(v); np.random.seed(v); torch.manual_seed(v); torch.cuda.manual_seed_all(v)
def predict(model,loader,device):
    model.eval(); ys=[]; probs=[]
    with torch.no_grad():
        for b in loader:
            logits,_,_=model(b['joints'].to(device)); ys.extend(b['label'].numpy().astype(int)); probs.extend(torch.sigmoid(logits).cpu().numpy())
    return np.asarray(ys),np.asarray(probs)
def metrics(y,p,t):
    pred=(p>=t).astype(int)
    return {'rows':len(y),'accuracy':float(accuracy_score(y,pred)),'f1_macro':float(f1_score(y,pred,average='macro',zero_division=0)),'threshold':float(t),'confusion_matrix':confusion_matrix(y,pred,labels=[0,1]).tolist(),'report':classification_report(y,pred,labels=[0,1],target_names=['incorrect','correct'],output_dict=True,zero_division=0)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--split-dir',type=Path,required=True); ap.add_argument('--catalog',type=Path,required=True); ap.add_argument('--target-frames',type=int,default=48); ap.add_argument('--epochs',type=int,default=50); ap.add_argument('--patience',type=int,default=8); ap.add_argument('--batch-size',type=int,default=16); ap.add_argument('--lr',type=float,default=2e-4); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--exercises',default='ELBOW_FLEXION,HAND_OPENING'); args=ap.parse_args(); seed_all(args.seed)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); print(f'device={device}',flush=True); args.output.mkdir(parents=True,exist_ok=True); results=[]
    for ex in args.exercises.split(','):
        ex=ex.strip(); train=DatanewRepDataset(args.split_dir/'train_manifest.csv',args.catalog,ex,args.target_frames,True); val=DatanewRepDataset(args.split_dir/'val_manifest.csv',args.catalog,ex,args.target_frames); test=DatanewRepDataset(args.split_dir/'test_manifest.csv',args.catalog,ex,args.target_frames)
        labels=np.array([int(r['completion_label']=='correct') for r in train.rows]); counts=np.bincount(labels,minlength=2); weights=np.array([1/max(1,counts[x]) for x in labels]); sampler=WeightedRandomSampler(weights,len(weights),replacement=True)
        tl=DataLoader(train,batch_size=args.batch_size,sampler=sampler); vl=DataLoader(val,batch_size=args.batch_size); xl=DataLoader(test,batch_size=args.batch_size)
        model=RehabCTRTCN(ex).to(device); opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=1e-4); loss_fn=torch.nn.BCEWithLogitsLoss(); best=None; best_f1=-1.; stale=0; best_t=.5
        for epoch in range(1,args.epochs+1):
            model.train(); losses=[]
            for b in tl:
                opt.zero_grad(set_to_none=True); logits,_,_=model(b['joints'].to(device)); loss=loss_fn(logits,b['label'].to(device)); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); losses.append(loss.item())
            y,p=predict(model,vl,device); candidates=np.linspace(.2,.8,25); scores=[f1_score(y,p>=t,average='macro',zero_division=0) for t in candidates]; pos=int(np.argmax(scores)); score=float(scores[pos]); threshold=float(candidates[pos])
            print(f'[{ex}] epoch={epoch:03d} loss={np.mean(losses):.4f} val_f1={score:.4f} threshold={threshold:.3f}',flush=True)
            if score>best_f1+1e-6: best_f1=score; best_t=threshold; stale=0; best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            else: stale+=1
            if stale>=args.patience: break
        model.load_state_dict(best); vy,vp=predict(model,vl,device); ty,tp=predict(model,xl,device); result={'exercise':ex,'epochs':epoch,'counts':{'train':len(train),'val':len(val),'test':len(test),'train_classes':counts.tolist()},'validation':metrics(vy,vp,best_t),'test':metrics(ty,tp,best_t)}; results.append(result)
        torch.save({'model':model.state_dict(),'exercise':ex,'threshold':best_t,'target_frames':args.target_frames,'metrics':result},args.output/f'{ex.lower()}.pth'); print(f'[{ex}] test_f1={result["test"]["f1_macro"]:.4f}',flush=True)
    payload={'status':'complete','protocol':'fixed video-disjoint expert rep temporal','architecture':'3-stream CTR-GCN + MS-TCN','seed':args.seed,'device':str(device),'target_frames':args.target_frames,'results':results}; (args.output/'metrics.json').write_text(json.dumps(payload,indent=2),encoding='utf-8'); print(json.dumps({'status':'complete','output':str((args.output/'metrics.json').resolve())},indent=2),flush=True)
if __name__=='__main__': main()
