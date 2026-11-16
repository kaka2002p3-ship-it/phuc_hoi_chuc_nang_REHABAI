"""Real-data loader and exercise-specific normalization for RehabCTR-TCN."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from shared.preprocessing.sequence import resample_sequence

EXERCISES = {"ELBOW_EXTENSION": 2, "HAND_OPENING": 4}


def _best_hand(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    def score(hand):
        valid = np.any(np.abs(hand) > 1e-7, axis=-1)
        motion = np.abs(np.diff(hand, axis=0)).sum()
        return float(valid.mean()) + float(motion) * 1e-3
    return left if score(left) >= score(right) else right


def normalize_hand(hand: np.ndarray) -> np.ndarray:
    value = hand.astype(np.float32, copy=True)
    missing = ~np.any(np.abs(value) > 1e-7, axis=-1)
    origin = value[:, 0:1]
    scale = np.linalg.norm(value[:, 9] - value[:, 0], axis=-1)
    fallback = np.linalg.norm(value[:, 5] - value[:, 17], axis=-1)
    scale = np.where(scale > 1e-5, scale, fallback)
    scale = np.where(scale > 1e-5, scale, 1.0)[:, None, None]
    value = (value - origin) / scale
    value[missing] = 0
    return value


def normalize_elbow(pose: np.ndarray) -> np.ndarray:
    # Select the arm with the largest reliable wrist trajectory.
    sides = ([11, 13, 15, 19], [12, 14, 16, 20])
    def score(indices):
        arm = pose[:, indices, :3]
        valid = np.any(np.abs(arm) > 1e-7, axis=-1).mean()
        return float(valid) + float(np.abs(np.diff(arm[:, 2], axis=0)).sum()) * 1e-3
    indices = sides[0] if score(sides[0]) >= score(sides[1]) else sides[1]
    value = pose[:, indices, :3].astype(np.float32, copy=True)
    missing = ~np.any(np.abs(value) > 1e-7, axis=-1)
    origin = value[:, 0:1]
    scale = np.linalg.norm(value[:, 1] - value[:, 0], axis=-1)
    scale = np.where(scale > 1e-5, scale, 1.0)[:, None, None]
    value = (value - origin) / scale
    value[missing] = 0
    return value


class ExerciseSpecificDataset(Dataset):
    def __init__(self, manifest: str | Path, data_dir: str | Path, exercise: str,
                 train: bool = False, target_frames: int = 96):
        self.exercise = exercise
        self.data_dir = Path(data_dir)
        self.train = train
        self.target_frames = target_frames
        table = pd.read_csv(manifest, dtype={"subject_id": str})
        table = table[(table.exercise_id == EXERCISES[exercise]) &
                      table.quality_gate_passed.astype(str).str.lower().isin(["true", "1"]) &
                      table.processed_exists.astype(str).str.lower().isin(["true", "1"])]
        table = table[table.sample_id.map(lambda value: (self.data_dir / str(value)).is_file())]
        self.records = table.to_dict("records")

    def __len__(self): return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        with np.load(self.data_dir / record["sample_id"], allow_pickle=False) as data:
            if self.exercise == "HAND_OPENING":
                joints = normalize_hand(_best_hand(data["left_hand_landmarks"], data["right_hand_landmarks"]))
            else:
                joints = normalize_elbow(data["pose_landmarks"])
        joints = resample_sequence(joints, self.target_frames).astype(np.float32)
        if self.train:
            joints = joints * np.float32(np.random.uniform(.97, 1.03))
            joints += np.random.normal(0, .003, joints.shape).astype(np.float32)
        return {"joints": torch.from_numpy(joints),
                "label": torch.tensor(float(record["completion_label"]), dtype=torch.float32),
                "sample_id": record["sample_id"], "subject_id": record["subject_id"]}
