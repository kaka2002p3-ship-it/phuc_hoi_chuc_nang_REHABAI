import copy
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.evaluate import CLASS_MAPPING, run_evaluation
from scripts.export_model import export_model_bundle
from scripts.generate_loso import hash_manifest
from shared.provenance import (
    VERIFICATION_KEY_ENV,
    build_provenance_record,
    canonical_provenance_hash,
    check_eligibility,
    check_physical_eligibility,
    verify_and_grant_real_verified,
)
from training.checkpoint_utils import compute_file_sha256, save_checkpoint
from training.datasets.feature_validation import validate_feature_arrays
from training.model_registry import get_model

TEST_KEY = "rev31-completion-authority-key-at-least-32-bytes"


@pytest.fixture(autouse=True)
def authority(monkeypatch):
    monkeypatch.setenv(VERIFICATION_KEY_ENV, TEST_KEY)


def _feature_arrays(frames=8):
    return {
        "pose_landmarks": np.zeros((frames, 33, 4), dtype=np.float32),
        "left_hand_landmarks": np.zeros((frames, 21, 3), dtype=np.float32),
        "right_hand_landmarks": np.zeros((frames, 21, 3), dtype=np.float32),
        "kinematics": np.zeros((frames, 12), dtype=np.float32),
    }


def _verified_record(source: Path, processed: Path, source_root: Path, processed_root: Path):
    candidate = build_provenance_record(
        source_video_path=str(source),
        subject_id="subject_01",
        exercise_id=1,
        completion_label=1.0,
        extraction_status="success",
        extractor_version="mediapipe-1.0",
        processed_path=str(processed),
        quality_gate_passed=True,
        compute_hash=True,
    )
    candidate["fold_id"] = "fold_01"
    candidate["split"] = "test"
    return verify_and_grant_real_verified(
        candidate,
        str(source_root),
        str(processed_root),
        verification_key=TEST_KEY,
    )


def _evaluation_bundle(tmp_path: Path):
    source_root = tmp_path / "source"
    processed_root = tmp_path / "processed"
    nested_source = source_root / "subject_01"
    nested_processed = processed_root / "subject_01"
    nested_source.mkdir(parents=True)
    nested_processed.mkdir(parents=True)
    source = nested_source / "clip.mp4"
    processed = nested_processed / "clip.npz"
    source.write_bytes(b"physical-source")
    np.savez(processed, **_feature_arrays())

    record = _verified_record(source, processed, source_root, processed_root)
    manifest = tmp_path / "test_manifest.csv"
    pd.DataFrame([record]).to_csv(manifest, index=False)
    records = pd.read_csv(manifest).to_dict("records")
    test_hash = hash_manifest(records)
    provenance_hash = hash_manifest(records)
    train_hash = "a" * 64
    val_hash = "b" * 64

    fold_metadata = {
        "fold_id": "fold_01",
        "canonical_provenance_manifest_hash": provenance_hash,
        "canonical_train_manifest_hash": train_hash,
        "canonical_val_manifest_hash": val_hash,
        "canonical_test_manifest_hash": test_hash,
    }
    fold_metadata_path = tmp_path / "fold_metadata.json"
    fold_metadata_path.write_text(json.dumps(fold_metadata), encoding="utf-8")

    norm = {
        "metadata": {
            "schema_version": "1.1",
            "fold_id": "fold_01",
            **{key: value for key, value in fold_metadata.items() if key.startswith("canonical_")},
            "feature_dimension": 12,
        },
        "kinematics": {"mean": [0.0] * 12, "std": [1.0] * 12},
    }
    norm_path = tmp_path / "norm.json"
    norm_path.write_text(json.dumps(norm), encoding="utf-8")

    model_name = "mlp"
    model_config = {"input_dim": 237, "num_exercises": 4}
    model_config_path = tmp_path / "training_model_config.json"
    model_config_path.write_text(json.dumps(model_config), encoding="utf-8")
    mapping_path = tmp_path / "class_mapping.json"
    mapping_path.write_text(json.dumps(CLASS_MAPPING), encoding="utf-8")

    checkpoint = tmp_path / "model.pth"
    save_checkpoint(
        model=get_model(model_name, model_config),
        optimizer=None,
        epoch=1,
        filepath=str(checkpoint),
        model_id=model_name,
        fold_id="fold_01",
        protocol_version="1.1",
        provenance_hash=provenance_hash,
        train_manifest_hash=train_hash,
        normalization_hash=compute_file_sha256(str(norm_path)),
        class_mapping=CLASS_MAPPING,
        model_config=model_config,
        architecture_signature="baseline_mlp_v1",
        checkpoint_role="supervised_model",
    )
    job = {
        "fold_id": "fold_01",
        "model_name": model_name,
        "data_dir": str(processed_root),
        "source_dir": str(source_root),
        "split_manifest": str(manifest),
        "normalization_json": str(norm_path),
        "checkpoint_path": str(checkpoint),
        "fold_metadata_path": str(fold_metadata_path),
        "expected_model_config": model_config,
        "expected_architecture_signature": "baseline_mlp_v1",
        "expected_class_mapping": CLASS_MAPPING,
    }
    return {
        "job": job,
        "fold_metadata": fold_metadata_path,
        "norm": norm_path,
        "model_config": model_config_path,
        "class_mapping": mapping_path,
        "checkpoint": checkpoint,
    }


def test_authority_signature_rejects_forged_evidence(tmp_path):
    source = tmp_path / "source.mp4"
    processed = tmp_path / "processed.npz"
    source.write_bytes(b"source")
    np.savez(processed, **_feature_arrays())
    record = _verified_record(source, processed, tmp_path, tmp_path)

    evidence = json.loads(record["verification_evidence"])
    evidence["verified_at"] = "2030-01-01T00:00:00+00:00"
    record["verification_evidence"] = json.dumps(evidence, sort_keys=True)
    record["provenance_hash"] = canonical_provenance_hash(record)
    ok, reason = check_eligibility(record)
    assert not ok
    assert "authority signature" in reason


def test_physical_gate_requires_source_root(tmp_path):
    ok, reason = check_physical_eligibility({}, data_dir=str(tmp_path), source_dir="")
    assert not ok
    assert "source_dir" in reason


@pytest.mark.parametrize(
    "key,bad_shape",
    [
        ("pose_landmarks", (8, 33, 3)),
        ("left_hand_landmarks", (8, 20, 3)),
        ("right_hand_landmarks", (8, 21, 4)),
        ("kinematics", (8, 11)),
    ],
)
def test_exact_feature_shapes_are_enforced(key, bad_shape):
    arrays = _feature_arrays()
    arrays[key] = np.zeros(bad_shape, dtype=np.float32)
    with pytest.raises(ValueError, match=f"Invalid {key} shape"):
        validate_feature_arrays(arrays, "fixture.npz")


def test_empty_and_non_numeric_features_are_rejected():
    arrays = _feature_arrays(frames=1)
    arrays["pose_landmarks"] = np.zeros((0, 33, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="Empty sequence"):
        validate_feature_arrays(arrays, "fixture.npz")
    arrays = _feature_arrays()
    arrays["kinematics"] = np.full((8, 12), "bad", dtype="<U3")
    with pytest.raises(TypeError, match="real numeric"):
        validate_feature_arrays(arrays, "fixture.npz")


def test_verifier_rejects_sibling_prefix_escape(tmp_path):
    allowed = tmp_path / "data"
    sibling = tmp_path / "database"
    allowed.mkdir()
    sibling.mkdir()
    source = sibling / "source.mp4"
    processed = allowed / "processed.npz"
    source.write_bytes(b"source")
    np.savez(processed, **_feature_arrays())
    candidate = build_provenance_record(
        str(source), "subject_01", 1, 1.0, "success", "mediapipe-1.0",
        processed_path=str(processed), quality_gate_passed=True, compute_hash=True,
    )
    with pytest.raises(ValueError, match="outside"):
        verify_and_grant_real_verified(candidate, str(allowed), str(allowed), TEST_KEY)


def test_verifier_rejects_symlink_escape_when_supported(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "source.mp4"
    processed = allowed / "processed.npz"
    source.write_bytes(b"source")
    np.savez(processed, **_feature_arrays())
    link = allowed / "source-link.mp4"
    try:
        link.symlink_to(source)
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable on this Windows host: {exc}")
    candidate = build_provenance_record(
        str(link), "subject_01", 1, 1.0, "success", "mediapipe-1.0",
        processed_path=str(processed), quality_gate_passed=True, compute_hash=True,
    )
    with pytest.raises(ValueError, match="outside"):
        verify_and_grant_real_verified(candidate, str(allowed), str(allowed), TEST_KEY)


@pytest.mark.parametrize(
    "model_name,config",
    [
        ("mlp", {"input_dim": 237, "num_exercises": 4}),
        ("lstm", {"input_dim": 237, "num_exercises": 4, "hidden_size": 8, "num_layers": 1}),
        ("bilstm", {"input_dim": 237, "num_exercises": 4, "hidden_size": 8, "num_layers": 1}),
        ("tcn", {"input_dim": 237, "num_exercises": 4, "channels": [8, 8]}),
        ("stgcn", {"input_dim": 237, "num_exercises": 4}),
        ("RehabModel", {"num_classes": 4, "hidden_dim": 16, "nhead": 4, "num_layers": 1, "dropout": 0.0}),
        ("RehabMotionNetEncoder", {"input_dim": 237, "hidden_dim": 8, "channels": [6, 6]}),
        ("RehabMotionNet", {"num_exercises": 4, "use_hand": False, "use_kinematic": False, "use_contrastive": False, "use_mstcn": False, "use_attention": False}),
    ],
)
def test_registry_instantiates_real_models(model_name, config):
    model = get_model(model_name, config)
    model.eval()
    with torch.no_grad():
        output = model(torch.zeros(2, 4, 237))
    assert output is not None


def test_evaluation_preflights_all_jobs_before_inference(tmp_path, monkeypatch):
    bundle = _evaluation_bundle(tmp_path)
    bad_job = copy.deepcopy(bundle["job"])
    bad_metadata = tmp_path / "bad_fold_metadata.json"
    metadata = json.loads(bundle["fold_metadata"].read_text(encoding="utf-8"))
    metadata["fold_id"] = "wrong_fold"
    bad_metadata.write_text(json.dumps(metadata), encoding="utf-8")
    bad_job["fold_metadata_path"] = str(bad_metadata)
    config = tmp_path / "evaluation.json"
    config.write_text(json.dumps({"jobs": [bundle["job"], bad_job], "output_file": str(tmp_path / "result.json")}), encoding="utf-8")

    calls = []
    monkeypatch.setattr("scripts.evaluate.evaluate_fold", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(ValueError, match="Fold metadata mismatch"):
        run_evaluation(str(config))
    assert calls == []
    assert not (tmp_path / "result.json").exists()


def test_evaluation_valid_job_writes_complete_result(tmp_path):
    bundle = _evaluation_bundle(tmp_path)
    output = tmp_path / "result.json"
    config = tmp_path / "evaluation.json"
    config.write_text(json.dumps({"jobs": [bundle["job"]], "output_file": str(output)}), encoding="utf-8")
    metrics = run_evaluation(str(config))
    assert len(metrics) == 1
    assert output.is_file()
    assert "f1_weighted" in metrics[0]
    assert set(metrics[0]["per_class"]) == {"0", "1", "2", "3"}
    assert np.asarray(metrics[0]["confusion_matrix"]).shape == (4, 4)
    assert json.loads(output.read_text(encoding="utf-8"))[0]["fold_id"] == "fold_01"


def test_exporter_builds_verified_bundle(tmp_path):
    bundle = _evaluation_bundle(tmp_path)
    output = tmp_path / "artifact"
    result = export_model_bundle(
        checkpoint=str(bundle["checkpoint"]),
        fold_metadata_path=str(bundle["fold_metadata"]),
        norm_json=str(bundle["norm"]),
        model_name="mlp",
        model_config_path=str(bundle["model_config"]),
        class_mapping_path=str(bundle["class_mapping"]),
        architecture_signature="baseline_mlp_v1",
        output_dir=str(output),
        fold_id="fold_01",
    )
    assert result == output.resolve()
    assert (output / "model.pt").is_file()
    assert (output / "bundle_sha256.json").is_file()


def test_exporter_failure_preserves_existing_bundle(tmp_path, monkeypatch):
    bundle = _evaluation_bundle(tmp_path)
    output = tmp_path / "artifact"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_text("old-valid-bundle", encoding="utf-8")
    monkeypatch.setattr(torch.jit, "trace", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace failed")))
    with pytest.raises(RuntimeError, match="trace failed"):
        export_model_bundle(
            checkpoint=str(bundle["checkpoint"]),
            fold_metadata_path=str(bundle["fold_metadata"]),
            norm_json=str(bundle["norm"]),
            model_name="mlp",
            model_config_path=str(bundle["model_config"]),
            class_mapping_path=str(bundle["class_mapping"]),
            architecture_signature="baseline_mlp_v1",
            output_dir=str(output),
            fold_id="fold_01",
        )
    assert sentinel.read_text(encoding="utf-8") == "old-valid-bundle"
    assert not list(tmp_path.glob(".artifact.staging-*"))


def test_verify_manifest_uses_authorized_physical_path(tmp_path):
    from scripts.verify_provenance import verify_manifest

    source_root = tmp_path / "sources"
    processed_root = tmp_path / "processed"
    source_root.mkdir()
    processed_root.mkdir()
    source = source_root / "clip.mp4"
    processed = processed_root / "clip.npz"
    source.write_bytes(b"source")
    np.savez(processed, **_feature_arrays())
    candidate = build_provenance_record(
        str(source), "subject_01", 1, 1.0, "success", "mediapipe-1.0",
        processed_path=str(processed), quality_gate_passed=True, compute_hash=True,
    )
    input_csv = tmp_path / "candidates.csv"
    output_csv = tmp_path / "verified.csv"
    pd.DataFrame([candidate]).to_csv(input_csv, index=False)
    verify_manifest(
        str(input_csv),
        str(output_csv),
        str(source_root),
        str(processed_root),
        verification_key=TEST_KEY,
    )
    verified = pd.read_csv(output_csv).to_dict("records")[0]
    ok, reason = check_physical_eligibility(
        verified,
        data_dir=str(processed_root),
        source_dir=str(source_root),
        verification_key=TEST_KEY,
    )
    assert ok, reason


def test_proposed_trainer_strict_contrastive_bootstrap(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from training.models.shared_encoder import SharedMotionEncoder
    from training.proposed_trainer import train_proposed

    source_root = tmp_path / "sources"
    processed_root = tmp_path / "processed"
    source_root.mkdir()
    processed_root.mkdir()
    records = []
    for index, split in enumerate(("train", "val"), start=1):
        source = source_root / f"clip-{index}.mp4"
        processed = processed_root / f"clip-{index}.npz"
        source.write_bytes(f"source-{index}".encode("utf-8"))
        np.savez(processed, **_feature_arrays())
        record = _verified_record(source, processed, source_root, processed_root)
        record["split"] = split
        records.append(record)

    train_manifest = tmp_path / "train.csv"
    val_manifest = tmp_path / "val.csv"
    pd.DataFrame([records[0]]).to_csv(train_manifest, index=False)
    pd.DataFrame([records[1]]).to_csv(val_manifest, index=False)
    train_records = pd.read_csv(train_manifest).to_dict("records")
    val_records = pd.read_csv(val_manifest).to_dict("records")
    provenance_hash = hash_manifest(train_records + val_records)
    train_hash = hash_manifest(train_records)
    val_hash = hash_manifest(val_records)
    norm = {
        "metadata": {
            "schema_version": "1.1",
            "fold_id": "fold_01",
            "canonical_provenance_manifest_hash": provenance_hash,
            "canonical_train_manifest_hash": train_hash,
            "canonical_val_manifest_hash": val_hash,
            "canonical_test_manifest_hash": "c" * 64,
            "feature_dimension": 12,
        },
        "kinematics": {"mean": [0.0] * 12, "std": [1.0] * 12},
    }
    norm_path = tmp_path / "norm.json"
    norm_path.write_text(json.dumps(norm), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    checkpoint_dir = tmp_path / "training" / "checkpoints" / "fold_01"
    checkpoint_dir.mkdir(parents=True)
    checkpoint = checkpoint_dir / "RehabMotionNetEncoder_fold_01_pretrained_encoder.pth"
    save_checkpoint(
        model=SharedMotionEncoder(),
        optimizer=None,
        epoch=0,
        filepath=str(checkpoint),
        model_id="RehabMotionNetEncoder",
        fold_id="fold_01",
        protocol_version="1.1",
        provenance_hash=provenance_hash,
        train_manifest_hash=train_hash,
        normalization_hash=compute_file_sha256(str(norm_path)),
        class_mapping={0: "SSL"},
        model_config={"use_hand": True, "use_kinematic": True, "use_attention": True},
        architecture_signature="rehab_motionnet_encoder_v1",
        checkpoint_role="pretrained_encoder",
    )
    args = SimpleNamespace(
        data_dir=str(processed_root),
        source_dir=str(source_root),
        train_manifest=str(train_manifest),
        val_manifest=str(val_manifest),
        norm_json=str(norm_path),
        fold_id="fold_01",
        use_hand=True,
        use_kinematic=True,
        use_contrastive=True,
        use_mstcn=True,
        use_attention=True,
        batch_size=1,
        lr=1e-3,
        weight_decay=0.0,
        epochs=0,
    )
    train_proposed(args)
