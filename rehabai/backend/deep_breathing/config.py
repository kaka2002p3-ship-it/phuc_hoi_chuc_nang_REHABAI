from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DeepBreathingConfig:
    """MVP defaults; every runtime threshold is exposed and configurable."""

    protocol_version: str = "v1"
    inhale_seconds: float = 4.0
    hold_seconds: float = 0.0
    exhale_seconds: float = 6.0
    rest_seconds: float = 0.0
    target_cycles: int = 6
    calibration_seconds: float = 2.0
    min_landmark_visibility: float = 0.60
    min_good_frames_ratio: float = 0.70
    ema_alpha: float = 0.20
    rise_threshold: float = 0.010
    fall_threshold: float = -0.010
    neutral_threshold: float = 0.004
    min_phase_frames: int = 5
    short_gap_frames: int = 3
    long_gap_frames: int = 15
    max_normalized_jump: float = 0.08
    min_cycle_seconds: float = 4.0
    max_cycle_seconds: float = 20.0
    count_cooldown_seconds: float = 1.0
    body_motion_threshold: float = 0.12

    @property
    def cycle_seconds(self) -> float:
        return self.inhale_seconds + self.hold_seconds + self.exhale_seconds + self.rest_seconds

    def __post_init__(self) -> None:
        positive = ("inhale_seconds", "exhale_seconds", "calibration_seconds", "cycle_seconds")
        for name in positive:
            if name != "cycle_seconds" and getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.hold_seconds < 0 or self.rest_seconds < 0:
            raise ValueError("hold_seconds and rest_seconds cannot be negative")
        if self.target_cycles < 1:
            raise ValueError("target_cycles must be at least one")
        if not 0 < self.min_landmark_visibility <= 1:
            raise ValueError("min_landmark_visibility must be in (0, 1]")
        if not 0 < self.min_good_frames_ratio <= 1:
            raise ValueError("min_good_frames_ratio must be in (0, 1]")
        if not 0 < self.ema_alpha <= 1:
            raise ValueError("ema_alpha must be in (0, 1]")
        if self.short_gap_frames < 0 or self.long_gap_frames <= self.short_gap_frames:
            raise ValueError("gap frame limits are invalid")
        if self.min_cycle_seconds <= 0 or self.max_cycle_seconds < self.min_cycle_seconds:
            raise ValueError("cycle duration limits are invalid")
        if not self.min_cycle_seconds <= self.cycle_seconds <= self.max_cycle_seconds:
            raise ValueError("guided protocol duration must stay within cycle duration limits")

    def as_dict(self) -> dict:
        return {**asdict(self), "cycle_seconds": self.cycle_seconds}

    @classmethod
    def from_env(cls) -> "DeepBreathingConfig":
        """Read optional deployment overrides without scattering magic numbers."""
        defaults = cls()
        values: dict[str, object] = {}
        float_fields = {
            "inhale_seconds", "hold_seconds", "exhale_seconds", "rest_seconds", "calibration_seconds",
            "min_landmark_visibility", "min_good_frames_ratio", "ema_alpha", "rise_threshold",
            "fall_threshold", "neutral_threshold", "max_normalized_jump", "min_cycle_seconds",
            "max_cycle_seconds", "count_cooldown_seconds", "body_motion_threshold",
        }
        int_fields = {"target_cycles", "min_phase_frames", "short_gap_frames", "long_gap_frames"}
        for field in float_fields | int_fields:
            key = f"REHABAI_BREATH_{field.upper()}"
            raw = os.getenv(key)
            if raw is None or not raw.strip():
                continue
            try:
                values[field] = float(raw) if field in float_fields else int(raw)
            except ValueError as exc:
                raise ValueError(f"Invalid {key}: {raw!r}") from exc
        return cls(**{**defaults.__dict__, **values})
