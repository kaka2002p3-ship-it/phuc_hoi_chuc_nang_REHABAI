"""Stable model contract independent of LSTM/BiLSTM/GRU/Transformer details."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
import numpy as np

@dataclass(frozen=True)
class PredictionResult:
    prediction: str
    confidence: float
    movement_quality: float | None
    feedback: str
    timestamp: str
    exercise_id: int | None = None
    joint_angles: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class BaseRehabModel(ABC):
    architecture: str = "unknown"

    @abstractmethod
    def predict(self, sequence: np.ndarray) -> PredictionResult:
        """Predict from a normalized landmark sequence; never synthesize input."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Return immutable model/artifact version."""

def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
