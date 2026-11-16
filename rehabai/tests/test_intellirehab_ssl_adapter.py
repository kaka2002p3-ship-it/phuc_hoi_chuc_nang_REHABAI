import numpy as np
import pandas as pd
import pytest
import torch

from scripts.prepare_intellirehabds_ssl_features import KINECT_TO_MEDIAPIPE, repair_common_joints
from training.intellirehab_ssl import ContrastiveSkeletonDataset
from training.model_registry import get_model
from training.models.rehab_motionnet import OptimizedSSLAdapter


def test_converter_mapping_uses_only_common_pose_and_no_hands():
    assert set(KINECT_TO_MEDIAPIPE.values()) == {11, 12, 13, 14, 15, 16, 23, 24}
    assert not any(33 <= index < 75 for index in KINECT_TO_MEDIAPIPE.values())


def test_converter_safely_interpolates_one_frame_tracking_gap():
    joints = np.ones((30, 25, 3), dtype=np.float32)
    joints[:, 4, 0] = np.arange(30)
    joints[12, 4] = 0
    repaired, frames, values = repair_common_joints(joints)
    assert frames == 1
    assert values == 1
    assert repaired[12, 4, 0] == pytest.approx(12.0)
    assert np.all(repaired[12, 4, 1:] == 1.0)


def test_converter_rejects_long_tracking_gap():
    joints = np.ones((30, 25, 3), dtype=np.float32)
    joints[10:16, 4] = 0
    with pytest.raises(ValueError, match="Unsafe missing-data gap"):
        repair_common_joints(joints)


def test_ssl_augmentation_is_reproducible_per_epoch_and_sample(tmp_path):
    path = tmp_path / "sample.npz"
    np.savez_compressed(path, features=np.ones((96, 237), dtype=np.float32))
    frame = pd.DataFrame([{"sample_id": "sample", "ssl_feature_path": str(path)}])
    first = ContrastiveSkeletonDataset(frame, train=True, seed=42)
    second = ContrastiveSkeletonDataset(frame, train=True, seed=42)
    first.set_epoch(3)
    second.set_epoch(3)
    a1, b1 = first[0]
    a2, b2 = second[0]
    assert torch.equal(a1, a2)
    assert torch.equal(b1, b2)
    first.set_epoch(4)
    a3, _ = first[0]
    assert not torch.equal(a1, a3)


def test_optimized_ssl_adapter_contract_and_frozen_encoder():
    model = OptimizedSSLAdapter(adapter_dim=16, adapter_dropout=0.0)
    x = torch.randn(2, 96, 237)
    exercise, completion = model(x)
    assert exercise.shape == (2, 4)
    assert completion.shape == (2, 1)
    assert all(not parameter.requires_grad for parameter in model.ssl_encoder.parameters())
    model.train()
    assert model.ssl_encoder.training is False
    common = model.common_view(x)
    assert torch.count_nonzero(common[:, :, 99:225]) == 0
    populated = set(OptimizedSSLAdapter.COMMON_POSE_JOINTS)
    for joint in range(33):
        if joint not in populated:
            assert torch.count_nonzero(common[:, :, joint * 3:joint * 3 + 3]) == 0


def test_optimized_ssl_adapter_registry_is_strict():
    assert isinstance(get_model("OptimizedSSLAdapter", {"adapter_dim": 16}), OptimizedSSLAdapter)
    with pytest.raises(ValueError, match="Unsupported config keys"):
        get_model("OptimizedSSLAdapter", {"unknown": True})
