from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BreathPhase(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    INHALE = "INHALE"
    HOLD = "HOLD"
    EXHALE = "EXHALE"
    REST = "REST"
    UNKNOWN = "UNKNOWN"
    TRACKING_INSUFFICIENT = "TRACKING_INSUFFICIENT"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class TrackingQuality(str, Enum):
    GOOD = "GOOD"
    MEDIUM = "MEDIUM"
    POOR = "POOR"
    UNAVAILABLE = "UNAVAILABLE"


class SignalQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class SessionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    CANCELLED = "CANCELLED"
    TRACKING_INSUFFICIENT = "TRACKING_INSUFFICIENT"
    ERROR = "ERROR"


@dataclass(frozen=True)
class PoseFrame:
    left_shoulder: tuple[float, float, float] | None = None
    right_shoulder: tuple[float, float, float] | None = None
    left_visibility: float = 0.0
    right_visibility: float = 0.0
    left_hip: tuple[float, float, float] | None = None
    right_hip: tuple[float, float, float] | None = None
    nose: tuple[float, float, float] | None = None

    @property
    def visible(self) -> bool:
        return self.left_shoulder is not None and self.right_shoulder is not None


@dataclass(frozen=True)
class SignalSample:
    valid: bool
    signal: float | None
    velocity: float | None
    tracking_quality: TrackingQuality
    signal_quality: SignalQuality
    outlier: bool = False
    missing_frames: int = 0
    artifact_detected: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
