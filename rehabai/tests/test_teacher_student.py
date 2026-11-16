import pandas as pd
import torch
import pytest

from training.teacher_student import consistency_loss, pseudo_labels, validate_distillation_manifests


def test_confidence_filter_is_fail_closed():
    labels, confidence, mask = pseudo_labels(torch.tensor([[5.0, 0.0], [0.01, 0.0]]), 0.9)
    assert labels.tolist() == [0, 0]
    assert mask.tolist() == [True, False]
    assert confidence[0] > confidence[1]


def test_consistency_loss_zero_when_no_pseudo_label():
    student = torch.tensor([[0.1, 0.2]], requires_grad=True)
    teacher = torch.tensor([[0.01, 0.0]])
    loss = consistency_loss(student, teacher, confidence_threshold=0.99)
    assert float(loss) == 0.0


def test_manifest_leakage_is_rejected(tmp_path):
    train = pd.DataFrame({"sample_id": ["a"], "subject_id": ["01"], "fold_id": ["fold_01"], "split": ["train"]})
    val = pd.DataFrame({"sample_id": ["b"], "subject_id": ["01"], "fold_id": ["fold_01"], "split": ["val"]})
    train_path, val_path = tmp_path / "train.csv", tmp_path / "val.csv"
    train.to_csv(train_path, index=False); val.to_csv(val_path, index=False)
    with pytest.raises(ValueError, match="subject leakage"):
        validate_distillation_manifests(str(train_path), str(val_path), "fold_01")
