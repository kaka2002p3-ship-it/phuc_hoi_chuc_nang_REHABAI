import torch
from training.models.ctr_gcn import UpperLimbCTRGCN
from training.model_registry import get_model

def test_ctr_gcn_output_contract():
    model = UpperLimbCTRGCN()
    ex, comp = model(torch.randn(2, 96, 237))
    assert ex.shape == (2, 4)
    assert comp.shape == (2, 1)

def test_ctr_gcn_registry():
    model = get_model("UpperLimbCTRGCN", {"upper_limb_only": True})
    assert isinstance(model, UpperLimbCTRGCN)
