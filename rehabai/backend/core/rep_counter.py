"""Experimental rule-based repetition counter for four upper-limb exercises."""

from collections import deque
from dataclasses import dataclass
from math import acos, degrees
from time import monotonic
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class RepThreshold:
    low: float
    high: float
    active_at: str = "high"


THRESHOLDS = {
    1: RepThreshold(28.0, 58.0, "low"),  # shoulder elevation angle (degrees)
    2: RepThreshold(82.0, 148.0),   # elbow angle (degrees)
    3: RepThreshold(72.0, 125.0),   # forearm-hand angle (degrees)
    4: RepThreshold(1.15, 1.65),    # fingertip distance / palm width
}


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> Optional[float]:
    v1, v2 = a - b, c - b
    n1, n2 = float(np.linalg.norm(v1)), float(np.linalg.norm(v2))
    if n1 < 1e-5 or n2 < 1e-5:
        return None
    cosine = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return degrees(acos(cosine))


def _pose_angle(pose: np.ndarray, side: int, exercise_id: int) -> Optional[float]:
    if exercise_id == 1:
        shoulder, elbow, hip = (11, 13, 23) if side == 0 else (12, 14, 24)
        return _angle(pose[hip, :3], pose[shoulder, :3], pose[elbow, :3])
    shoulder, elbow, wrist = (11, 13, 15) if side == 0 else (12, 14, 16)
    return _angle(pose[shoulder, :3], pose[elbow, :3], pose[wrist, :3])


def _wrist_angle(pose: np.ndarray, hand: Optional[np.ndarray], side: int) -> Optional[float]:
    if hand is None or hand.shape != (21, 3) or not np.any(np.abs(hand) > 1e-6):
        return None
    elbow, wrist = (13, 15) if side == 0 else (14, 16)
    return _angle(pose[elbow, :3], pose[wrist, :3], hand[9, :3])


def _hand_open_ratio(hand: Optional[np.ndarray]) -> Optional[float]:
    if hand is None or hand.shape != (21, 3) or not np.any(np.abs(hand) > 1e-6):
        return None
    palm_width = float(np.linalg.norm(hand[5] - hand[17]))
    if palm_width < 1e-5:
        return None
    tips = hand[[4, 8, 12, 16, 20]]
    return float(np.mean(np.linalg.norm(tips - hand[0], axis=1)) / palm_width)


class RuleBasedRepCounter:
    def __init__(self, exercise_id: int, confirm_frames: int = 3, cooldown_s: float = 0.7):
        if exercise_id not in THRESHOLDS:
            raise ValueError(f"Unsupported exercise_id: {exercise_id}")
        self.exercise_id = exercise_id
        self.threshold = THRESHOLDS[exercise_id]
        self.confirm_frames = confirm_frames
        self.cooldown_s = cooldown_s
        self.values = deque(maxlen=5)
        self.side_values = {0: deque(maxlen=30), 1: deque(maxlen=30)}
        self.active_side: Optional[int] = None
        self.state = "REST"
        self.high_frames = self.low_frames = self.rep_count = 0
        self.last_rep_at = -1e9
        self.last_value: Optional[float] = None

    def _signal(self, pose, left_hand, right_hand) -> Optional[float]:
        if self.exercise_id == 4:
            candidates = [_hand_open_ratio(left_hand), _hand_open_ratio(right_hand)]
        elif self.exercise_id == 3:
            candidates = [_wrist_angle(pose, left_hand, 0), _wrist_angle(pose, right_hand, 1)]
        else:
            candidates = [_pose_angle(pose, side, self.exercise_id) for side in (0, 1)]
        for side, value in enumerate(candidates):
            if value is not None and np.isfinite(value):
                self.side_values[side].append(float(value))
        if self.active_side is None:
            ranges = {side: (max(values) - min(values) if len(values) >= 5 else -1.0) for side, values in self.side_values.items()}
            minimum_range = 0.08 if self.exercise_id == 4 else 8.0
            if max(ranges.values()) >= minimum_range:
                self.active_side = max(ranges, key=ranges.get)
        if self.active_side is not None:
            selected = candidates[self.active_side]
            return float(selected) if selected is not None and np.isfinite(selected) else None
        valid = [value for value in candidates if value is not None and np.isfinite(value)]
        # Before side lock, accept only an unambiguous single detected side.
        return float(valid[0]) if len(valid) == 1 else None

    def update(self, pose, left_hand, right_hand, quality_ready: bool) -> dict:
        if not quality_ready or pose.shape != (33, 3):
            return self.snapshot(False)
        value = self._signal(pose, left_hand, right_hand)
        if value is None:
            return self.snapshot(False)
        self.values.append(value)
        value = float(np.median(np.asarray(self.values)))
        self.last_value = value
        if self.threshold.active_at == "low":
            active, rest = value <= self.threshold.low, value >= self.threshold.high
        else:
            active, rest = value >= self.threshold.high, value <= self.threshold.low
        if active:
            self.high_frames += 1; self.low_frames = 0
        elif rest:
            self.low_frames += 1; self.high_frames = 0
        else:
            self.high_frames = self.low_frames = 0
        if self.state == "REST" and self.high_frames >= self.confirm_frames:
            self.state = "ACTIVE"
        elif self.state == "ACTIVE" and self.low_frames >= self.confirm_frames:
            now = monotonic()
            if now - self.last_rep_at >= self.cooldown_s:
                self.rep_count += 1; self.last_rep_at = now
            self.state = "REST"
        return self.snapshot(True)

    def snapshot(self, quality_ready=True) -> dict:
        return {"rep_count": self.rep_count, "state": self.state, "signal": self.last_value,
                "quality_ready": quality_ready, "estimated": True,
                "threshold_low": self.threshold.low, "threshold_high": self.threshold.high,
                "active_side": self.active_side}
