from __future__ import annotations

from collections import deque
from statistics import median
from typing import Iterable

from .config import DeepBreathingConfig
from .types import PoseFrame, SignalQuality, SignalSample, TrackingQuality


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


class MotionSignalProcessor:
    """Visibility gate -> normalization -> outlier rejection -> EMA/velocity."""

    def __init__(self, config: DeepBreathingConfig):
        self.config = config
        self._baseline_y: float | None = None
        self._baseline_scale: float | None = None
        self._ema: float | None = None
        self._previous: float | None = None
        self._missing = 0
        self._history: deque[float] = deque(maxlen=30)
        self._baseline_nose: tuple[float, float] | None = None
        self._baseline_center_x: float | None = None

    @property
    def calibrated(self) -> bool:
        return self._baseline_y is not None and self._baseline_scale is not None

    @property
    def baseline_noise(self) -> float:
        if len(self._history) < 2:
            return 0.0
        values = list(self._history)
        center = median(values)
        return median([abs(value - center) for value in values])

    def calibrate(self, frames: Iterable[PoseFrame]) -> bool:
        frame_list = list(frames)
        ys: list[float] = []
        scales: list[float] = []
        noses: list[tuple[float, float]] = []
        centers_x: list[float] = []
        for frame in frame_list:
            if not self._is_visible(frame):
                continue
            shoulder_y = (frame.left_shoulder[1] + frame.right_shoulder[1]) / 2  # type: ignore[index]
            scale = self._scale(frame)
            if scale > 1e-6:
                ys.append(shoulder_y)
                scales.append(scale)
                centers_x.append((frame.left_shoulder[0] + frame.right_shoulder[0]) / 2)  # type: ignore[index]
                if frame.nose is not None:
                    noses.append((frame.nose[0], frame.nose[1]))
        if not frame_list or not ys or len(ys) / len(frame_list) < self.config.min_good_frames_ratio:
            return False
        self._baseline_y = median(ys)
        self._baseline_scale = median(scales)
        self._baseline_center_x = median(centers_x)
        self._baseline_nose = (median([p[0] for p in noses]), median([p[1] for p in noses])) if noses else None
        self._history.clear()
        self._history.extend(0.0 for _ in range(min(len(ys), self._history.maxlen or 0)))
        self._ema = 0.0
        self._previous = 0.0
        self._missing = 0
        return True

    def _is_visible(self, frame: PoseFrame) -> bool:
        return (
            frame.visible
            and frame.left_visibility >= self.config.min_landmark_visibility
            and frame.right_visibility >= self.config.min_landmark_visibility
        )

    def _scale(self, frame: PoseFrame) -> float:
        if frame.left_hip is not None and frame.right_hip is not None:
            shoulder_mid = tuple((frame.left_shoulder[i] + frame.right_shoulder[i]) / 2 for i in range(3))  # type: ignore[index]
            hip_mid = tuple((frame.left_hip[i] + frame.right_hip[i]) / 2 for i in range(3))
            torso = _distance(shoulder_mid, hip_mid)
            if torso > 1e-6:
                return torso
        return _distance(frame.left_shoulder, frame.right_shoulder)  # type: ignore[arg-type]

    def update(self, frame: PoseFrame) -> SignalSample:
        if not self.calibrated:
            return SignalSample(False, None, None, TrackingQuality.POOR, SignalQuality.UNKNOWN, missing_frames=self._missing)
        if not self._is_visible(frame):
            self._missing += 1
            quality = TrackingQuality.POOR if self._missing < self.config.long_gap_frames else TrackingQuality.UNAVAILABLE
            return SignalSample(False, None, None, quality, SignalQuality.UNKNOWN, missing_frames=self._missing)

        self._missing = 0
        shoulder_y = (frame.left_shoulder[1] + frame.right_shoulder[1]) / 2  # type: ignore[index]
        scale = max(self._scale(frame), 1e-6)
        normalized = -((shoulder_y - self._baseline_y) / max(self._baseline_scale, scale * 0.5))  # type: ignore[operator]
        previous = self._previous
        if previous is not None and abs(normalized - previous) > self.config.max_normalized_jump:
            return SignalSample(False, self._ema, 0.0, TrackingQuality.MEDIUM, SignalQuality.LOW, outlier=True)
        self._previous = normalized
        alpha = self.config.ema_alpha
        self._ema = normalized if self._ema is None else alpha * normalized + (1 - alpha) * self._ema
        # Use a short multi-frame trend rather than a single-frame delta. This
        # reduces phase flicker while preserving the configurable thresholds.
        trend_frames = min(len(self._history), self.config.min_phase_frames)
        reference = self._history[-trend_frames] if trend_frames else 0.0
        velocity = None if self._ema is None else self._ema - reference
        self._history.append(self._ema or 0.0)
        center_x = (frame.left_shoulder[0] + frame.right_shoulder[0]) / 2  # type: ignore[index]
        artifact = self._baseline_center_x is not None and abs(center_x - self._baseline_center_x) > self.config.body_motion_threshold
        if frame.nose is not None and self._baseline_nose is not None:
            # Compare with the calibrated user position, not the image centre.
            artifact = artifact or _distance(
                (frame.nose[0], frame.nose[1], 0.0),
                (self._baseline_nose[0], self._baseline_nose[1], 0.0),
            ) > self.config.body_motion_threshold
        trend = abs(velocity or 0.0)
        signal_quality = SignalQuality.HIGH if trend >= self.config.rise_threshold else SignalQuality.MEDIUM
        return SignalSample(True, self._ema, velocity, TrackingQuality.GOOD, signal_quality, artifact_detected=artifact)

    def reset(self) -> None:
        self._baseline_y = self._baseline_scale = self._ema = self._previous = None
        self._baseline_nose = None
        self._baseline_center_x = None
        self._missing = 0
        self._history.clear()
