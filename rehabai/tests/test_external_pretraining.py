import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from scripts.prepare_external_pretraining import MOBI_EXERCISES
from scripts.extract_external_keypoints import inspect_feature
from training.external_pretrain import ExternalMotionDataset, MultiSourcePretrainer, subjectwise_split
from training.models.rehab_motionnet import ExternalEncoderAdapter


def test_external_ontology_does_not_claim_product_mapping():
    policy = json.loads((Path(__file__).parents[1] / "data/external_pretraining_v1/dataset_policy.json").read_text(encoding="utf-8"))
    assert "no mapping to product classes" in policy["ontology_policy"]
    assert set(map(int, policy["mobiphysio"]["exercises"])) == set(MOBI_EXERCISES)


def test_external_dataset_contract(tmp_path):
    feature = tmp_path / "sample.npz"
    np.savez_compressed(feature, pose_landmarks=np.ones((40, 33, 3), np.float32))
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{
        "sample_id": "sample.npz", "dataset": "REHAB24-6", "subject_id": "R24_01",
        "source_exercise_id": 1, "correctness": 1, "quality_score": "",
        "feature_path": str(feature), "feature_status": "ready",
    }]).to_csv(manifest, index=False)
    x, source, exercise, correctness, quality = ExternalMotionDataset(manifest)[0]
    assert x.shape == (96, 237)
    assert (source, exercise, correctness, quality) == (0, 0, 1.0, -1.0)
    assert torch.isfinite(x).all()
    pose = x[:, :99].reshape(96, 33, 3)
    assert torch.count_nonzero(pose[:, [0, 1, 2, 23, 24]]) == 0


def test_mobiphysio_missing_hands_stay_zero(tmp_path):
    feature = tmp_path / "mobi.npz"
    pose = np.ones((40, 33, 3), np.float32)
    pose[:, 11, 0] = 0.25
    pose[:, 12, 0] = 0.75
    np.savez_compressed(
        feature,
        pose_landmarks=pose,
        left_hand_landmarks=np.zeros((40, 21, 3), np.float32),
        right_hand_landmarks=np.zeros((40, 21, 3), np.float32),
    )
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{
        "sample_id": "mobi.npz", "dataset": "MobiPhysio", "subject_id": "MOBI_01",
        "source_exercise_id": 1, "correctness": "", "quality_score": 80,
        "feature_path": str(feature), "feature_status": "ready",
    }]).to_csv(manifest, index=False)
    x, *_ = ExternalMotionDataset(manifest)[0]
    assert torch.count_nonzero(x[:, 99:225]) == 0


def test_existing_external_feature_recovers_missing_rate(tmp_path):
    feature = tmp_path / "external.npz"
    pose = np.ones((96, 33, 3), np.float32)
    pose[:12] = 0
    np.savez_compressed(
        feature,
        pose_landmarks=pose,
        left_hand_landmarks=np.zeros((96, 21, 3), np.float32),
        right_hand_landmarks=np.zeros((96, 21, 3), np.float32),
    )
    status = inspect_feature(feature, 96)
    assert status is not None
    assert status[0] == "ready"
    assert status[1] == 0.125


def test_invalid_existing_external_feature_is_not_reused(tmp_path):
    feature = tmp_path / "invalid.npz"
    np.savez_compressed(feature, pose_landmarks=np.ones((95, 33, 3), np.float32))
    assert inspect_feature(feature, 96) is None


def test_multisource_model_heads_are_separate():
    model = MultiSourcePretrainer()
    output = model(torch.zeros(2, 96, 237))
    assert output[1].shape == (2, 6)
    assert output[2].shape == (2, 6)
    assert model.r24_exercise.weight.data_ptr() != model.mobi_exercise.weight.data_ptr()


def test_external_validation_split_is_subject_disjoint(tmp_path):
    rows = []
    for dataset in ("REHAB24-6", "MobiPhysio"):
        for subject in range(4):
            feature = tmp_path / f"{dataset}_{subject}.npz"
            np.savez_compressed(feature, pose_landmarks=np.ones((40, 33, 3), np.float32))
            rows.append({
                "sample_id": feature.name,
                "dataset": dataset,
                "subject_id": f"{dataset}_{subject}",
                "source_exercise_id": 1,
                "correctness": 1 if dataset == "REHAB24-6" else "",
                "quality_score": 80 if dataset == "MobiPhysio" else "",
                "feature_path": str(feature),
                "feature_status": "ready",
            })
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    dataset = ExternalMotionDataset(manifest)
    train, validation, validation_subjects = subjectwise_split(dataset, 0.25, 42)
    train_subjects = set(dataset.frame.iloc[train].subject_id)
    validation_subject_ids = set(dataset.frame.iloc[validation].subject_id)
    assert train_subjects.isdisjoint(validation_subject_ids)
    assert set(validation_subjects) == {"REHAB24-6", "MobiPhysio"}
    assert len(train) + len(validation) == len(dataset)


def test_external_adapter_keeps_encoder_frozen_in_train_mode():
    model = ExternalEncoderAdapter(adapter_dim=16, adapter_dropout=0.0)
    model.freeze_encoder()
    model.train()
    assert not model.pretrained_encoder.training
    assert all(not parameter.requires_grad for parameter in model.pretrained_encoder.parameters())
    exercise, completion = model(torch.zeros(2, 8, 237))
    assert exercise.shape == (2, 4)
    assert completion.shape == (2, 1)
