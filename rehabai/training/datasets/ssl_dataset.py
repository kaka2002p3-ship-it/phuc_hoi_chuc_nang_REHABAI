import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
import torch
from torch.utils.data import Dataset
from shared.preprocessing.sequence import resample_sequence
from shared.preprocessing.augmentation import add_gaussian_noise, random_rotation_y, random_landmark_masking
from shared.provenance import check_physical_eligibility
from scripts.generate_loso import hash_manifest
from training.datasets.feature_validation import validate_feature_arrays, KINEMATICS_DIM

class SSLRehabDataset(Dataset):
    """
    Unlabeled dataset for Self-Supervised Learning.
    Returns two augmented views of the same sequence.
    """
    def __init__(self, data_dir: str, source_dir: str, train_manifest_csv: str, normalization_json: str, fold_id: str):
        self.data_dir = Path(data_dir)
        self.source_dir = Path(source_dir)
        self.target_frames = 96
        self.fold_id = fold_id
        
        if not source_dir or not os.path.exists(source_dir):
            raise ValueError(f"source_dir is required in strict research mode: {source_dir}")
            
        if not data_dir or not os.path.exists(data_dir):
            raise ValueError(f"data_dir is required in strict research mode: {data_dir}")
        
        if not os.path.exists(train_manifest_csv):
            raise FileNotFoundError(f"Train manifest not found: {train_manifest_csv}")
            
        if not os.path.exists(normalization_json):
            raise FileNotFoundError(f"Normalization schema not found: {normalization_json}")
            
        # Load Normalization schema first
        with open(normalization_json, "r") as f:
            schema = json.load(f)
            
        if 'metadata' not in schema or 'kinematics' not in schema:
            raise KeyError("Normalization schema missing 'metadata' or 'kinematics' key")
            
        norm_fold = schema['metadata'].get('fold_id')
        if norm_fold != self.fold_id:
             raise ValueError(f"Normalization artifact fold mismatch: expected {self.fold_id}, got {norm_fold}")
             
        expected_dim = schema['metadata'].get('feature_dimension', -1)
        expected_prov_hash = schema['metadata'].get('canonical_provenance_manifest_hash')
        expected_train_hash = schema['metadata'].get('canonical_train_manifest_hash')
            
        self.kin_mean = np.array(schema['kinematics']['mean'], dtype=np.float32)
        self.kin_std = np.array(schema['kinematics']['std'], dtype=np.float32)
        if expected_dim != KINEMATICS_DIM:
            raise ValueError(f"Normalization feature_dimension must be {KINEMATICS_DIM}, got {expected_dim}")
        if self.kin_mean.shape != (KINEMATICS_DIM,) or self.kin_std.shape != (KINEMATICS_DIM,):
            raise ValueError("Normalization mean/std must each contain exactly 12 values")
        if not np.isfinite(self.kin_mean).all() or not np.isfinite(self.kin_std).all() or (self.kin_std <= 0).any():
            raise ValueError("Normalization mean/std must be finite and std must be positive")

        # Load index
        df = pd.read_csv(train_manifest_csv, dtype={"subject_id": str})
        
        required_cols = ['sample_id', 'subject_id', 'fold_id', 'split', 'data_status', 'extraction_status', 'quality_gate_passed']
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Missing canonical required column '{col}' in manifest. Legacy manifests are rejected.")
        
        records = df.to_dict('records')
        loaded_manifest_hash = hash_manifest(records)
        
        if loaded_manifest_hash != expected_train_hash:
             raise ValueError(f"Train manifest hash mismatch! Expected {expected_train_hash}, got {loaded_manifest_hash}")

        self.files = []
        seen_samples = set()
        
        for record in records:
            sample_id = record['sample_id']
            if sample_id in seen_samples:
                raise ValueError(f"Duplicate sample_id found in manifest: {sample_id}")
            if record['split'] != 'train':
                raise ValueError(f"SSL Dataset strictly requires split='train'. Found '{record['split']}' in {sample_id}")
            if record['fold_id'] != self.fold_id:
                raise ValueError(f"Record {sample_id} fold {record['fold_id']} does not match expected {self.fold_id}")

            ok, reason = check_physical_eligibility(
                record, data_dir=str(self.data_dir), source_dir=str(self.source_dir)
            )
            if not ok:
                raise ValueError(f"Ineligible record found in train manifest: {sample_id} - {reason}")
            seen_samples.add(sample_id)
            
            file_path = self.data_dir / sample_id
                
            with np.load(file_path, allow_pickle=False) as data:
                validate_feature_arrays(data, str(file_path), expected_dim)

            self.files.append(sample_id)
            
        if len(self.files) == 0:
            raise ValueError("No eligible samples found in the SSL train manifest.")

    def __len__(self):
        return len(self.files)
        
    def _apply_augmentation(self, pose, lh, rh, prob_noise, prob_rot, prob_mask):
        # pose: (T, 33, 3)
        # lh, rh: (T, 21, 3)
        
        if np.random.rand() < prob_noise:
            pose = add_gaussian_noise(pose, std=0.01)
            lh = add_gaussian_noise(lh, std=0.005)
            rh = add_gaussian_noise(rh, std=0.005)
            
        if np.random.rand() < prob_rot:
            pose = random_rotation_y(pose, max_angle_degrees=20)
            lh = random_rotation_y(lh, max_angle_degrees=20)
            rh = random_rotation_y(rh, max_angle_degrees=20)
            
        if np.random.rand() < prob_mask:
            pose = random_landmark_masking(pose, prob=0.1)
            lh = random_landmark_masking(lh, prob=0.15)
            rh = random_landmark_masking(rh, prob=0.15)
            
        return pose, lh, rh

    def _process_view(self, data, is_view1):
        pose = data['pose_landmarks'][..., :3] # (N, 33, 3)
        lh = data['left_hand_landmarks'] # (N, 21, 3)
        rh = data['right_hand_landmarks'] # (N, 21, 3)
        kin = data['kinematics'] # (N, 12)
        
        # Standard scale kinematics
        kin = (kin - self.kin_mean) / self.kin_std
        
        # Apply stochastic augmentations
        # View 1 and View 2 get different random augmentations
        if is_view1:
            pose, lh, rh = self._apply_augmentation(pose, lh, rh, 0.8, 0.5, 0.2)
        else:
            pose, lh, rh = self._apply_augmentation(pose, lh, rh, 0.2, 0.8, 0.8)
            
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
        return torch.tensor(features, dtype=torch.float32)

    def __getitem__(self, idx):
        file_path = self.data_dir / self.files[idx]
        data = np.load(file_path, allow_pickle=False)
        
        view1 = self._process_view(data, is_view1=True)
        view2 = self._process_view(data, is_view1=False)
        
        return view1, view2
