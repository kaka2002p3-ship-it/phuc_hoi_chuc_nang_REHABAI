"""Rule-based NECK_LATERAL_STRETCH pipeline.

This exercise deliberately does not use the trained exercise classifier.  It
consumes Pose landmarks, calibrates a per-user centre, and only emits a rep
after a complete target/hold/return state-machine cycle.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import atan2, degrees
from statistics import median
from typing import Optional

import numpy as np


NECK_LATERAL_STRETCH_ID = 6
NECK_CONFIG = {
    "center_tolerance_deg": 6.0, "center_exit_deg": 8.0,
    "target_min_deg": 15.0, "target_max_deg": 30.0, "target_exit_deg": 13.0,
    "return_tolerance_deg": 7.0, "hold_seconds": 3.0,
    "min_landmark_visibility": 0.60, "min_good_frames_ratio": 0.70,
    "max_shoulder_tilt_deg": 8.0, "angle_ema_alpha": 0.25,
    "max_angle_jump_deg": 12.0, "short_gap_frames": 3, "long_gap_frames": 10,
    "min_phase_ms": 250, "rep_cooldown_ms": 800,
    "max_moving_seconds": 8.0, "max_hold_seconds": 10.0, "max_return_seconds": 8.0,
    "target_mode": "PERSONALIZED_CALIBRATION",
}


def normalize_angle(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def relative_head_tilt(pose: np.ndarray) -> Optional[float]:
    """Ear-line angle relative to shoulder-line angle; negative is LEFT."""
    if pose.shape[0] < 13:
        return None
    required = pose[[7, 8, 11, 12], :2]  # ears, shoulders
    if not np.all(np.isfinite(required)) or np.allclose(required, 0):
        return None
    left_ear, right_ear, left_shoulder, right_shoulder = required
    ear = degrees(atan2(float(right_ear[1] - left_ear[1]), float(right_ear[0] - left_ear[0])))
    shoulder = degrees(atan2(float(right_shoulder[1] - left_shoulder[1]), float(right_shoulder[0] - left_shoulder[0])))
    value = normalize_angle(ear - shoulder)
    # Image y grows downwards: make a rightward visual tilt positive.
    return float(-value)


def shoulder_tilt(pose: np.ndarray) -> Optional[float]:
    if pose.shape[0] < 13:
        return None
    a, b = pose[11, :2], pose[12, :2]
    if not np.all(np.isfinite([*a, *b])) or np.allclose([*a, *b], 0):
        return None
    return degrees(atan2(float(b[1] - a[1]), float(b[0] - a[0])))


@dataclass
class NeckUpdate:
    state: str
    rep_count: int
    left_reps: int
    right_reps: int
    interrupted_reps: int
    angle: Optional[float]
    baseline: Optional[float]
    tracking_quality: str
    compensation_detected: bool
    hold_seconds: float


class NeckLateralStretchCounter:
    def __init__(self, config: Optional[dict] = None):
        self.config = {**NECK_CONFIG, **(config or {})}
        self.reset()

    def reset(self):
        self.state = "IDLE"; self.baseline = None; self.baseline_shoulder = None
        self._calibration: list[float] = []; self._calibration_poses: list[np.ndarray] = []
        self._smooth = None; self._last_raw = None; self._hold_started = None
        self._phase_started = None; self._side = None; self._last_ts = None
        self._last_rep_ts = None; self._missing_frames = 0
        self.rep_count = self.left_reps = self.right_reps = self.interrupted_reps = 0

    def _interrupt_active_rep(self):
        if self.state in {"MOVING_LEFT", "MOVING_RIGHT", "HOLD_LEFT", "HOLD_RIGHT",
                          "RETURNING_FROM_LEFT", "RETURNING_FROM_RIGHT"}:
            self.interrupted_reps += 1
        self._side = None; self._hold_started = None; self._phase_started = None

    def calibrate(self, frames: list[np.ndarray]) -> bool:
        values = [relative_head_tilt(x) for x in frames]
        shoulders = [shoulder_tilt(x) for x in frames]
        values = [x for x in values if x is not None]; shoulders = [x for x in shoulders if x is not None]
        ratio = len(values) / max(len(frames), 1)
        if ratio < self.config["min_good_frames_ratio"]:
            self.state = "TRACKING_INSUFFICIENT"; return False
        self.baseline, self.baseline_shoulder = float(median(values)), float(median(shoulders or [0]))
        self.state = "CENTER"; return True

    def update(self, pose: np.ndarray, timestamp: float, quality_ready: bool = True) -> dict:
        self._last_ts = float(timestamp)
        if not quality_ready:
            self._missing_frames += 1
            if self._missing_frames > self.config["long_gap_frames"]:
                self._interrupt_active_rep()
                if self.state not in {"IDLE", "COMPLETED"}: self.state = "TRACKING_INSUFFICIENT"
            return self.snapshot("POOR")
        self._missing_frames = 0
        raw, shoulder = relative_head_tilt(pose), shoulder_tilt(pose)
        if raw is None or shoulder is None:
            return self.snapshot("POOR")
        if self.baseline is None:
            self._calibration.append(raw); self._calibration_poses.append(pose.copy())
            if len(self._calibration) >= 30: self.calibrate(self._calibration_poses)
            return self.snapshot("CALIBRATING")
        relative = normalize_angle(raw - self.baseline)
        if self._last_raw is not None and abs(relative - self._last_raw) > self.config["max_angle_jump_deg"]:
            # Reject this frame for transitions, but advance the raw reference
            # so a genuine movement is accepted on the following frame.
            self._last_raw = relative
            return self.snapshot("GOOD")
        self._last_raw = relative
        alpha = self.config["angle_ema_alpha"]
        self._smooth = relative if self._smooth is None else alpha * relative + (1 - alpha) * self._smooth
        compensation = abs(shoulder - (self.baseline_shoulder or 0)) > self.config["max_shoulder_tilt_deg"]
        now = float(timestamp)
        if compensation:
            return self.snapshot("GOOD", compensation)
        a = float(self._smooth); tol = self.config["center_tolerance_deg"]
        if self.state == "TRACKING_INSUFFICIENT":
            self.state = "CENTER" if abs(a) <= tol else "PAUSED"
            return self.snapshot("GOOD")
        if self.state == "PAUSED":
            if abs(a) <= tol: self.state = "CENTER"
            return self.snapshot("GOOD")
        if self.state == "CENTER":
            if a < -tol: self.state, self._side, self._phase_started = "MOVING_LEFT", "LEFT", now
            elif a > tol: self.state, self._side, self._phase_started = "MOVING_RIGHT", "RIGHT", now
        elif self.state in {"MOVING_LEFT", "MOVING_RIGHT"}:
            if now - (self._phase_started or now) > self.config["max_moving_seconds"]: self.interrupted_reps += 1; self.state = "CENTER"
            elif (now - (self._phase_started or now)) * 1000 >= self.config["min_phase_ms"] and self.config["target_min_deg"] <= abs(a) <= self.config["target_max_deg"]: self.state = "HOLD_LEFT" if self._side == "LEFT" else "HOLD_RIGHT"; self._hold_started = now
        elif self.state in {"HOLD_LEFT", "HOLD_RIGHT"}:
            if abs(a) < self.config["target_exit_deg"]: self.state = "MOVING_LEFT" if self._side == "LEFT" else "MOVING_RIGHT"; self._hold_started = None
            elif now - (self._hold_started or now) >= self.config["hold_seconds"]: self.state = "RETURNING_FROM_LEFT" if self._side == "LEFT" else "RETURNING_FROM_RIGHT"
        elif self.state in {"RETURNING_FROM_LEFT", "RETURNING_FROM_RIGHT"} and abs(a) <= self.config["return_tolerance_deg"]:
            cooldown_ok = self._last_rep_ts is None or (now - self._last_rep_ts) * 1000 >= self.config["rep_cooldown_ms"]
            if cooldown_ok:
                self.rep_count += 1; self.left_reps += self._side == "LEFT"; self.right_reps += self._side == "RIGHT"; self._last_rep_ts = now
            self.state = "CENTER"; self._side = None; self._hold_started = None; self._phase_started = None
        return self.snapshot("GOOD", compensation)

    def snapshot(self, quality: str, compensation: bool = False) -> dict:
        return {"state": self.state, "rep_count": self.rep_count, "left_reps": self.left_reps, "right_reps": self.right_reps,
                "interrupted_reps": self.interrupted_reps, "angle": self._smooth, "baseline": self.baseline,
                "tracking_quality": quality, "compensation_detected": compensation,
                "hold_seconds": 0.0 if self._hold_started is None or self._last_ts is None else max(0.0, self._last_ts - self._hold_started)}
