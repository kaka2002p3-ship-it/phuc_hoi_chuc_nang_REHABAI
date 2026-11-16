import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from shared.preprocessing.sequence import resample_sequence
from shared.preprocessing.augmentation import add_gaussian_noise, random_rotation_y, random_landmark_masking
from shared.provenance import check_physical_eligibility
from scripts.generate_loso import hash_manifest
from training.datasets.feature_validation import validate_feature_arrays, KINEMATICS_DIM

class RehabDataset(Dataset):
    def __init__(self, data_dir: str, source_dir: str, split_manifest_csv: str, split: str, 
                 normalization_json: str, fold_id: str, apply_augmentation: bool = False):
        """
        data_dir: Path to processed .npz files (e.g., data/processed/keypoints)
        source_dir: Path to raw source videos
        split_manifest_csv: Path to specific fold manifest (e.g. data/indexes/loso/fold_01/train_manifest.csv)
        split: 'train', 'val', or 'test' (must match the manifest content conceptually)
        normalization_json: Path to fold-specific normalization schema
        fold_id: Target fold ID (e.g., 'fold_01')
        """
        self.data_dir = Path(data_dir)
        self.source_dir = Path(source_dir)
        self.target_frames = 96
        self.apply_augmentation = apply_augmentation
        self.split = split
        self.fold_id = fold_id

        if split not in {"train", "val", "test"}:
            raise ValueError(f"Invalid split: {split}")
        
        if apply_augmentation and split != 'train':
            raise ValueError(f"Augmentation requested for non-train split: {split}. This is unsafe for evaluation.")
            
        if not source_dir or not os.path.exists(source_dir):
            raise ValueError(f"source_dir is required in strict research mode: {source_dir}")
            
        if not data_dir or not os.path.exists(data_dir):
            raise ValueError(f"data_dir is required in strict research mode: {data_dir}")

        if not os.path.exists(split_manifest_csv):
            raise FileNotFoundError(f"Manifest not found: {split_manifest_csv}")
            
        if not os.path.exists(normalization_json):
            raise FileNotFoundError(f"Normalization schema not found: {normalization_json}")

        # Load Normalization schema first to get invariants
        with open(normalization_json, "r") as f:
            schema = json.load(f)
            
        if 'metadata' not in schema or 'kinematics' not in schema:
            raise KeyError("Normalization schema missing 'metadata' or 'kinematics' key")
            
        if schema['metadata'].get('schema_version') != '1.1':
            raise ValueError("schema_version must be 1.1")
            
        norm_fold = schema['metadata'].get('fold_id')
        if norm_fold != self.fold_id:
             raise ValueError(f"Normalization artifact fold mismatch: expected {self.fold_id}, got {norm_fold}")
             
        expected_dim = schema['metadata'].get('feature_dimension', -1)
        expected_prov_hash = schema['metadata'].get('canonical_provenance_manifest_hash')
        expected_train_hash = schema['metadata'].get('canonical_train_manifest_hash')
        expected_val_hash = schema['metadata'].get('canonical_val_manifest_hash')
        expected_test_hash = schema['metadata'].get('canonical_test_manifest_hash')
            
        self.kin_mean = np.array(schema['kinematics']['mean'], dtype=np.float32)
        self.kin_std = np.array(schema['kinematics']['std'], dtype=np.float32)
        if expected_dim != KINEMATICS_DIM:
            raise ValueError(f"Normalization feature_dimension must be {KINEMATICS_DIM}, got {expected_dim}")
        if self.kin_mean.shape != (KINEMATICS_DIM,) or self.kin_std.shape != (KINEMATICS_DIM,):
            raise ValueError("Normalization mean/std must each contain exactly 12 values")
        if not np.isfinite(self.kin_mean).all() or not np.isfinite(self.kin_std).all() or (self.kin_std <= 0).any():
            raise ValueError("Normalization mean/std must be finite and std must be positive")

        # Load index
        # Subject IDs are canonical zero-padded strings ("01", "02", ...).
        # Letting pandas infer integers changes the signed manifest hash.
        df = pd.read_csv(split_manifest_csv, dtype={"subject_id": str})
        
        # We need the canonical schema columns
        required_cols = ['sample_id', 'subject_id', 'exercise_id', 'completion_label', 'fold_id', 'split', 'data_status', 'extraction_status', 'quality_gate_passed']
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Missing canonical required column '{col}' in manifest. Legacy manifests are rejected.")

        records = df.to_dict('records')
        loaded_manifest_hash = hash_manifest(records)
        
        if self.split == 'train':
            if loaded_manifest_hash != expected_train_hash:
                 raise ValueError(f"Train manifest hash mismatch! Expected {expected_train_hash}, got {loaded_manifest_hash}")
        elif self.split == 'val':
            if loaded_manifest_hash != expected_val_hash:
                 raise ValueError(f"Val manifest hash mismatch! Expected {expected_val_hash}, got {loaded_manifest_hash}")
        elif self.split == 'test':
            if loaded_manifest_hash != expected_test_hash:
                 raise ValueError(f"Test manifest hash mismatch! Expected {expected_test_hash}, got {loaded_manifest_hash}")

        self.files = []
        self.exercises = []
        self.completions = []
        
        # Track duplicate sample_ids
        seen_samples = set()
        
        for record in records:
            sample_id = record['sample_id']
            if sample_id in seen_samples:
                raise ValueError(f"Duplicate sample_id found in manifest: {sample_id}")
            if record['split'] != self.split:
                raise ValueError(f"Record {sample_id} split {record['split']} does not match dataset split {self.split}")
            if record['fold_id'] != self.fold_id:
                raise ValueError(f"Record {sample_id} fold {record['fold_id']} does not match dataset fold {self.fold_id}")

            ok, reason = check_physical_eligibility(
                record, data_dir=str(self.data_dir), source_dir=str(self.source_dir)
            )
            if not ok:
                raise ValueError(f"Ineligible record found in {self.split} manifest: {sample_id} - {reason}")
            seen_samples.add(sample_id)
            
            file_path = self.data_dir / sample_id
                
            with np.load(file_path, allow_pickle=False) as data:
                validate_feature_arrays(data, str(file_path), expected_dim)

            self.files.append(sample_id)
            
            # Label mapping
            ex_id = int(float(record['exercise_id']))
            if ex_id not in [1, 2, 3, 4]:
                raise ValueError(f"Invalid exercise_id {ex_id}")
            self.exercises.append(ex_id - 1) # Internal 0-index mapping
            
            comp_float = float(record['completion_label'])
            if comp_float not in [0.0, 1.0]:
                raise ValueError(f"Invalid completion_label {comp_float}")
            self.completions.append(comp_float)
            
        if len(self.files) == 0:
            raise ValueError(f"No eligible samples found in the {self.split} manifest.")

    def __len__(self):
        return len(self.files)
        
    def __getitem__(self, idx):
        file_path = self.data_dir / self.files[idx]
        data = np.load(file_path, allow_pickle=False)
        
        pose = data['pose_landmarks'][..., :3] # (N, 33, 3), drop visibility
        lh = data['left_hand_landmarks'] # (N, 21, 3)
        rh = data['right_hand_landmarks'] # (N, 21, 3)
        kin = data['kinematics'] # (N, 12)
        
        # Standard scale kinematics
        kin = (kin - self.kin_mean) / self.kin_std
        
        # Augmentation
        if self.apply_augmentation:
            if np.random.rand() < 0.5:
                pose = add_gaussian_noise(pose, std=0.01)
                lh = add_gaussian_noise(lh, std=0.005)
                rh = add_gaussian_noise(rh, std=0.005)
                
            if np.random.rand() < 0.5:
                pose = random_rotation_y(pose, max_angle_degrees=15)
                lh = random_rotation_y(lh, max_angle_degrees=15)
                rh = random_rotation_y(rh, max_angle_degrees=15)
                
            if np.random.rand() < 0.3:
                pose = random_landmark_masking(pose, prob=0.05)
                lh = random_landmark_masking(lh, prob=0.1)
                rh = random_landmark_masking(rh, prob=0.1)
                
        # Resample to target frames
        pose = resample_sequence(pose, self.target_frames)
        lh = resample_sequence(lh, self.target_frames)
        rh = resample_sequence(rh, self.target_frames)
        kin = resample_sequence(kin, self.target_frames)
        
        # Flatten spatial dimensions
        pose_flat = pose.reshape(self.target_frames, -1) # (T, 99)
        lh_flat = lh.reshape(self.target_frames, -1) # (T, 63)
        rh_flat = rh.reshape(self.target_frames, -1) # (T, 63)
        
        # Concatenate features
        features = np.concatenate([pose_flat, lh_flat, rh_flat, kin], axis=1) # (T, 237)
        
        ex_label = self.exercises[idx]
        comp_label = self.completions[idx]
        
        return {
            "features": torch.tensor(features, dtype=torch.float32),
            "exercise": torch.tensor(ex_label, dtype=torch.long),
            "completion": torch.tensor(comp_label, dtype=torch.float32) # float32 for BCEWithLogitsLoss
        }
