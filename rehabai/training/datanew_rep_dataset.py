"""Expert-reviewed repetition dataset backed by existing 96-frame NPZ files."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from shared.preprocessing.sequence import resample_sequence
from training.exercise_specific_data import _best_hand, normalize_hand, normalize_elbow

class DatanewRepDataset(Dataset):
    def __init__(self, manifest: str|Path, catalog: str|Path, exercise: str, target_frames=48, augment=False):
        table=pd.read_csv(manifest,dtype={'video_id':str}); cat=pd.read_csv(catalog,dtype={'sample_id':str})
        table=table[(table.exercise==exercise)&table.completion_label.isin(['correct','incorrect'])].copy()
        table=table.merge(cat[['sample_id','output']],left_on='video_id',right_on='sample_id',how='left',validate='many_to_one')
        table=table[table.output.map(lambda p: Path(str(p)).is_file())]
        self.rows=table.to_dict('records'); self.exercise=exercise; self.target_frames=target_frames; self.augment=augment
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        r=self.rows[index]; start=max(0,int(float(r['start_frame']))); end=min(95,int(float(r['end_frame'])))
        with np.load(r['output'],allow_pickle=False) as d:
            if self.exercise=='HAND_OPENING': value=normalize_hand(_best_hand(d['left_hand_landmarks'],d['right_hand_landmarks']))
            else: value=normalize_elbow(d['pose_landmarks'])
        value=value[start:end+1]
        if len(value)<2: raise RuntimeError(f"Invalid rep window: {r['video_id']}/{r['rep_id']}")
        value=resample_sequence(value,self.target_frames).astype(np.float32)
        if self.augment:
            value=value*np.float32(np.random.uniform(.97,1.03))+np.random.normal(0,.003,value.shape).astype(np.float32)
        return {'joints':torch.from_numpy(value),'label':torch.tensor(float(r['completion_label']=='correct'),dtype=torch.float32),'video_id':r['video_id'],'rep_id':int(r['rep_id'])}
