import numpy as np
from backend.ml.models.base import BaseRehabModel, PredictionResult, utc_timestamp

class MockModel(BaseRehabModel):
    architecture="mock"
    @property
    def version(self): return "test"
    def predict(self, sequence):
        return PredictionResult("complete",.91,.89,"Động tác đang được thực hiện đúng.",utc_timestamp())

def test_model_contract_without_gpu():
    result=MockModel().predict(np.zeros((96,237),dtype=np.float32))
    assert result.prediction=="complete" and result.confidence==.91

