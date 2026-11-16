"""Adapter from the existing TorchScript bundle to the stable ML contract."""
from __future__ import annotations
import numpy as np
from backend.ml.models.base import BaseRehabModel, PredictionResult, utc_timestamp

class ProductionModelAdapter(BaseRehabModel):
    architecture = "RehabMotionNet"
    def __init__(self, loader): self.loader = loader
    @property
    def version(self) -> str: return "model_v2"
    def predict(self, sequence: np.ndarray) -> PredictionResult:
        raw = self.loader.predict(sequence)
        return PredictionResult(prediction=f"exercise_{raw['exercise_id']}", exercise_id=int(raw["exercise_id"]),
            confidence=float(raw["confidence"]), movement_quality=None,
            feedback="Đã nhận diện bài tập; đánh giá chất lượng chi tiết chưa được xác thực.", timestamp=utc_timestamp())
