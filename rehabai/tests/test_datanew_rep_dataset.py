from pathlib import Path
import pandas as pd
from training.datanew_rep_dataset import DatanewRepDataset


def test_final_rep_dataset_loads_both_exercises():
    root=Path(__file__).resolve().parents[1]
    manifest=root/'data/annotations/datanew_expert_split_final_seed42/val_manifest.csv'
    catalog=root/'data/datanew_unlabeled/datanew_exercise_catalog.csv'
    for exercise,nodes in [('ELBOW_FLEXION',4),('HAND_OPENING',21)]:
        ds=DatanewRepDataset(manifest,catalog,exercise,target_frames=48)
        assert len(ds)>0
        item=ds[0]
        assert tuple(item['joints'].shape)==(48,nodes,3)
        assert item['label'].item() in {0.0,1.0}
