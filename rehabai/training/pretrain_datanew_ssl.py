"""Contrastive pretraining on datanew features (research artifact only)."""
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from training.models.shared_encoder import SharedMotionEncoder
from training.models.contrastive import SimCLR, NTXentLoss
from training.device import select_training_device
from shared.preprocessing.sequence import resample_sequence
from shared.preprocessing.augmentation import add_gaussian_noise, random_rotation_y, random_landmark_masking

class DatanewDataset(Dataset):
    def __init__(self, manifests: list[Path]):
        import pandas as pd
        frame = pd.concat([pd.read_csv(path).fillna("") for path in manifests], ignore_index=True)
        frame = frame[frame.status == "ready"]
        if len(frame) < 2: raise ValueError("Need at least two ready datanew features")
        self.paths = frame.output.tolist()
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        with np.load(self.paths[idx], allow_pickle=False) as d:
            pose = d["pose_landmarks"].astype(np.float32); lh = d["left_hand_landmarks"].astype(np.float32); rh = d["right_hand_landmarks"].astype(np.float32); kin = d["kinematics"].astype(np.float32)
        def view(seed):
            p, l, r = pose.copy(), lh.copy(), rh.copy()
            rng = np.random.default_rng(seed)
            if rng.random() < .8: p=add_gaussian_noise(p,.01); l=add_gaussian_noise(l,.005); r=add_gaussian_noise(r,.005)
            if rng.random() < .7: p=random_rotation_y(p,20); l=random_rotation_y(l,20); r=random_rotation_y(r,20)
            if rng.random() < .5: p=random_landmark_masking(p,.1); l=random_landmark_masking(l,.15); r=random_landmark_masking(r,.15)
            p=resample_sequence(p,96); l=resample_sequence(l,96); r=resample_sequence(r,96); k=resample_sequence(kin,96)
            return torch.tensor(np.concatenate([p.reshape(96,-1),l.reshape(96,-1),r.reshape(96,-1),k],1),dtype=torch.float32)
        return view(idx*2+1), view(idx*2+2)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',type=Path,required=True,nargs='+'); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--epochs',type=int,default=50); ap.add_argument('--batch-size',type=int,default=32); ap.add_argument('--lr',type=float,default=1e-3); ap.add_argument('--seed',type=int,default=42)
    a=ap.parse_args(); random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.cuda.manual_seed_all(a.seed)
    device=select_training_device(); ds=DatanewDataset(a.manifest); dl=DataLoader(ds,batch_size=min(a.batch_size,len(ds)),shuffle=True,drop_last=False)
    encoder=SharedMotionEncoder(); model=SimCLR(encoder).to(device); opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=1e-4); crit=NTXentLoss(temperature=.1); best=float('inf'); best_state=None; history=[]
    for epoch in range(a.epochs):
        model.train(); total=0.; n=0
        for v1,v2 in dl:
            if len(v1)<2: continue
            v1=v1.to(device); v2=v2.to(device); opt.zero_grad(set_to_none=True); z1,z2=model(v1,v2); loss=crit(z1,z2); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); total+=float(loss.item()); n+=1
        value=total/max(1,n); history.append({'epoch':epoch+1,'loss':value}); print(f'epoch={epoch+1}/{a.epochs} loss={value:.5f}',flush=True)
        if value<best and value>0: best=value; best_state={k:v.detach().cpu().clone() for k,v in encoder.state_dict().items()}
    if best_state is None: raise RuntimeError('No valid contrastive batch')
    h=hashlib.sha256()
    for manifest in a.manifest: h.update(manifest.read_bytes())
    digest=h.hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True); torch.save({'model_state_dict':best_state,'metadata':{'architecture_signature':'datanew_ssl_encoder_v1','input_contract':'common_upper_limb_237_v1','manifest_sha256':digest,'source_datasets':['datanew_unlabeled'],'ontology_mapping_to_product':None,'sample_count':len(ds),'seed':a.seed,'best_loss':best}},a.output)
    (a.output.parent/'training_summary.json').write_text(json.dumps({'sample_count':len(ds),'best_loss':best,'history':history},indent=2),encoding='utf-8'); print(f'saved={a.output}')
if __name__=='__main__': main()
