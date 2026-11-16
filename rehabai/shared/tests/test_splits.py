import os
import pandas as pd
import pytest

def test_no_data_leakage_between_splits():
    manifest_path = "data/indexes/splits/split_manifest.csv"
    if not os.path.exists(manifest_path):
        pytest.skip("split_manifest.csv not found. Skip split testing.")
        
    df = pd.read_csv(manifest_path)
    
    train_subs = set(df[df['split'] == 'train']['subject_id'].unique())
    val_subs = set(df[df['split'] == 'val']['subject_id'].unique())
    test_subs = set(df[df['split'] == 'test']['subject_id'].unique())
    
    # Assert mutual exclusivity
    assert train_subs.isdisjoint(val_subs), f"Leakage: Train and Val share subjects: {train_subs.intersection(val_subs)}"
    assert train_subs.isdisjoint(test_subs), f"Leakage: Train and Test share subjects: {train_subs.intersection(test_subs)}"
    assert val_subs.isdisjoint(test_subs), f"Leakage: Val and Test share subjects: {val_subs.intersection(test_subs)}"
    
def test_valid_exercise_ids():
    manifest_path = "data/indexes/splits/split_manifest.csv"
    if not os.path.exists(manifest_path):
        pytest.skip("split_manifest.csv not found.")
        
    df = pd.read_csv(manifest_path)
    
    # Check that exercise_id belongs to {1, 2, 3, 4}
    valid_ids = {1, 2, 3, 4}
    invalid_rows = df[~df['exercise_id'].isin(valid_ids)]
    assert len(invalid_rows) == 0, f"Found invalid exercise IDs: {invalid_rows['exercise_id'].unique()}"
