import os
import json
import pytest
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

from shared.provenance import (
    build_provenance_record, 
    check_eligibility, 
    check_physical_eligibility, 
    canonical_provenance_hash, 
    filter_or_reject_manifest,
    STATUS_REAL_VERIFIED,
    STATUS_REAL_CANDIDATE,
    verify_and_grant_real_verified,
    VERIFICATION_KEY_ENV,
)
from training.datasets.rehab_dataset import RehabDataset
from training.datasets.ssl_dataset import SSLRehabDataset
from training.checkpoint_utils import save_checkpoint, load_checkpoint_strict, compute_file_sha256
from training.normalization import fit_fold_normalization
from scripts.generate_loso import generate_loso_splits, hash_manifest
from scripts.evaluate import evaluate_fold

TEST_VERIFICATION_KEY = "stage2-test-verification-key-32-bytes-minimum"

@pytest.fixture(autouse=True)
def _verification_authority(monkeypatch):
    monkeypatch.setenv(VERIFICATION_KEY_ENV, TEST_VERIFICATION_KEY)

# Dummy Model for testing checkpoints
class DummyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(237, 2)
    def forward(self, x):
        return self.fc(x.mean(dim=1))

def build_test_record(sample_id, subject_id, exercise, completion, split, fold_id, data_status, ext_status, gate_passed, processed_path):
    r = build_provenance_record(
        source_video_path="dummy.mp4",
        subject_id=subject_id,
        exercise_id=exercise,
        completion_label=completion,
        extraction_status=ext_status,
        extractor_version="1.0.0",
        interim_path="dummy.npy",
        processed_path=processed_path,
        quality_gate_passed=gate_passed,
        compute_hash=False
    )
    r["split"] = split
    r["fold_id"] = fold_id
    r["data_status"] = data_status
    r["source_video_exists"] = True
    r["processed_exists"] = True
    r["exclusion_reasons"] = ""
    r["source_video_sha256"] = "b"*64
    r["processed_feature_sha256"] = "a"*64
    if data_status == STATUS_REAL_VERIFIED:
        r["verification_evidence"] = json.dumps({
            "verified_by": "strict_pipeline_v1",
            "verification_schema_version": "1.1",
            "verification_status": STATUS_REAL_VERIFIED,
            "verification_method": "physical_checksum_match",
            "source_checksum": "b"*64,
            "processed_checksum": "a"*64
        }, sort_keys=True)
        r["authorized_by"] = "Agent"
    r["provenance_hash"] = canonical_provenance_hash(r)
    return r

@pytest.fixture
def dummy_data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    # Create dummy source video
    (d / "dummy.mp4").write_text("dummy_video")
    for i in range(10):
        sample_id = f"sample_{i}.npz"
        np.savez(d / sample_id, kinematics=np.random.rand(96, 12), pose_landmarks=np.random.rand(96, 33, 4), left_hand_landmarks=np.random.rand(96, 21, 3), right_hand_landmarks=np.random.rand(96, 21, 3))
    return d

def _reverify_record(record, data_root):
    candidate = dict(record)
    candidate["data_status"] = STATUS_REAL_CANDIDATE
    candidate["source_video_path"] = str(Path(data_root) / candidate["source_record_id"])
    candidate["processed_feature_path"] = str(Path(data_root) / candidate["sample_id"])
    candidate["source_video_exists"] = True
    candidate["processed_exists"] = True
    candidate["source_video_sha256"] = ""
    candidate["processed_feature_sha256"] = ""
    candidate["exclusion_reasons"] = ""
    candidate.pop("verification_evidence", None)
    candidate.pop("provenance_hash", None)
    return verify_and_grant_real_verified(
        candidate,
        str(data_root),
        str(data_root),
        verification_key=TEST_VERIFICATION_KEY,
    )


def compute_and_update_manifest(manifest_path, sample_id, new_file_path):
    records = pd.read_csv(manifest_path).to_dict("records")
    for index, record in enumerate(records):
        if record["sample_id"] == sample_id:
            records[index] = _reverify_record(record, Path(new_file_path).parent)
    pd.DataFrame(records).to_csv(manifest_path, index=False)
    
def update_norm_json_hash(norm_json_path, manifest_path):
    df = pd.read_csv(manifest_path)
    new_hash = hash_manifest(df.to_dict('records'))
    with open(norm_json_path, 'r') as f:
        schema = json.load(f)
    schema["metadata"]["canonical_train_manifest_hash"] = new_hash
    schema["metadata"]["canonical_val_manifest_hash"] = new_hash
    schema["metadata"]["canonical_test_manifest_hash"] = new_hash
    with open(norm_json_path, 'w') as f:
        json.dump(schema, f)
    
def get_valid_record(dummy_data_dir, i):
    sample_id = f"sample_{i}.npz"
    candidate = build_provenance_record(
        source_video_path=str(dummy_data_dir / "dummy.mp4"),
        subject_id=f"subject_{i}",
        exercise_id=1,
        completion_label=1.0,
        extraction_status="success",
        extractor_version="1.0.0",
        interim_path=None,
        processed_path=str(dummy_data_dir / sample_id),
        quality_gate_passed=True,
        compute_hash=True,
    )
    candidate["split"] = "train"
    candidate["fold_id"] = "fold_01"
    return verify_and_grant_real_verified(
        candidate,
        str(dummy_data_dir),
        str(dummy_data_dir),
        verification_key=TEST_VERIFICATION_KEY,
    )

@pytest.fixture
def valid_manifest(dummy_data_dir, tmp_path):
    manifest_path = tmp_path / "train_manifest.csv"
    data = [get_valid_record(dummy_data_dir, i) for i in range(10)]
    df = pd.DataFrame(data)
    df.to_csv(manifest_path, index=False)
    return manifest_path

@pytest.fixture
def norm_json(tmp_path, valid_manifest):
    df = pd.read_csv(valid_manifest)
    manifest_hash = hash_manifest(df.to_dict('records'))
        
    norm_path = tmp_path / "norm.json"
    schema = {
        "metadata": {
            "schema_version": "1.1",
            "fold_id": "fold_01",
            "provenance_manifest_hash": "d"*64,
            "canonical_train_manifest_hash": manifest_hash,
            "canonical_val_manifest_hash": manifest_hash,
            "canonical_test_manifest_hash": manifest_hash,
            "feature_dimension": 12
        },
        "kinematics": {
            "mean": list(np.zeros(12)),
            "std": list(np.ones(12))
        }
    }
    with open(norm_path, "w") as f:
        json.dump(schema, f)
    return norm_path

# ==========================================
# Section 1: Dataset Integrity & Loaders (11 assertions)
# ==========================================
def test_dataset_req1_normalization_mismatch(dummy_data_dir, valid_manifest, norm_json):
    with pytest.raises(ValueError, match="Normalization artifact fold mismatch"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_02",
            apply_augmentation=False
        )

def test_dataset_req2_nan_check(dummy_data_dir, valid_manifest, norm_json):
    nan_file = dummy_data_dir / "sample_0.npz"
    bad_kin = np.random.rand(96, 12)
    bad_kin[0, 0] = np.nan
    np.savez(nan_file, kinematics=bad_kin, pose_landmarks=np.random.rand(96, 33, 4), left_hand_landmarks=np.random.rand(96, 21, 3), right_hand_landmarks=np.random.rand(96, 21, 3))
    compute_and_update_manifest(valid_manifest, "sample_0.npz", nan_file)
    update_norm_json_hash(norm_json, valid_manifest)
    with pytest.raises(ValueError, match="NaN or Inf"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req3_inf_check(dummy_data_dir, valid_manifest, norm_json):
    inf_file = dummy_data_dir / "sample_1.npz"
    bad_kin = np.random.rand(96, 12)
    bad_kin[0, 0] = np.inf
    np.savez(inf_file, kinematics=bad_kin, pose_landmarks=np.random.rand(96, 33, 4), left_hand_landmarks=np.random.rand(96, 21, 3), right_hand_landmarks=np.random.rand(96, 21, 3))
    compute_and_update_manifest(valid_manifest, "sample_1.npz", inf_file)
    update_norm_json_hash(norm_json, valid_manifest)
    with pytest.raises(ValueError, match="NaN or Inf"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req4_feature_dim_mismatch(dummy_data_dir, valid_manifest, norm_json):
    bad_dim_file = dummy_data_dir / "sample_2.npz"
    np.savez(bad_dim_file, kinematics=np.random.rand(96, 15), pose_landmarks=np.random.rand(96, 33, 4), left_hand_landmarks=np.random.rand(96, 21, 3), right_hand_landmarks=np.random.rand(96, 21, 3))
    compute_and_update_manifest(valid_manifest, "sample_2.npz", bad_dim_file)
    update_norm_json_hash(norm_json, valid_manifest)
    with pytest.raises(ValueError, match="Invalid kinematics shape"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req5_missing_split(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    df = pd.read_csv(valid_manifest)
    df.drop(columns=["split"], inplace=True)
    m = tmp_path / "bad.csv"
    df.to_csv(m, index=False)
    with pytest.raises(KeyError, match="Missing canonical required column"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(m),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req6_missing_status(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    df = pd.read_csv(valid_manifest)
    df.drop(columns=["data_status"], inplace=True)
    m = tmp_path / "bad.csv"
    df.to_csv(m, index=False)
    with pytest.raises(KeyError, match="Missing canonical required column"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(m),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req7_wrong_split(dummy_data_dir, valid_manifest, norm_json):
    with pytest.raises(ValueError, match="does not match dataset split"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="val",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req8_unverified_record(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    df = pd.read_csv(valid_manifest)
    df.loc[0, "data_status"] = "MOCK"
    m = tmp_path / "bad.csv"
    df.to_csv(m, index=False)
    update_norm_json_hash(norm_json, m)
    with pytest.raises(ValueError, match="Ineligible record found"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(m),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req9_duplicate_sample(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    df = pd.read_csv(valid_manifest)
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    m = tmp_path / "bad.csv"
    df.to_csv(m, index=False)
    update_norm_json_hash(norm_json, m)
    with pytest.raises(ValueError, match="Duplicate sample_id"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(m),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=False
        )

def test_dataset_req10_ssl_train_only(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    df = pd.read_csv(valid_manifest)
    df["split"] = "val"
    m = tmp_path / "bad.csv"
    df.to_csv(m, index=False)
    with pytest.raises(ValueError, match="SSL Dataset strictly requires split='train'"):
        SSLRehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            train_manifest_csv=str(m),
            normalization_json=norm_json,
            fold_id="fold_01"
        )

def test_dataset_req11_physical_check_missing(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    records = pd.read_csv(valid_manifest).to_dict("records")
    (dummy_data_dir / records[0]["sample_id"]).unlink()
    with pytest.raises(ValueError, match="processed feature"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="train",
            normalization_json=norm_json,
            fold_id="fold_01",
        )


def get_meta(h="h", th="train_hash", vh="val_hash", teh="test_hash"):
    return {
        "fold_id": "fold_01",
        "test_subject": "subject_test",
        "validation_subjects": ["subject_val"],
        "canonical_provenance_manifest_hash": h,
        "canonical_train_manifest_hash": th,
        "canonical_val_manifest_hash": vh,
        "canonical_test_manifest_hash": teh,
    }


def test_norm_req12_prevent_val_leakage(dummy_data_dir, valid_manifest, tmp_path):
    from shared.provenance import canonical_provenance_hash
    m = pd.read_csv(valid_manifest).to_dict('records')
    m[0]["split"] = "val"
    m[0]["subject_id"] = "subject_val"
    m[0]["provenance_hash"] = canonical_provenance_hash(m[0])
    with pytest.raises(ValueError, match="has wrong split"):
        fit_fold_normalization(m, get_meta(th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "norm.json"))

def test_norm_req13_zero_variance_replace(dummy_data_dir, valid_manifest, tmp_path):
    from shared.provenance import canonical_provenance_hash
    import json
    m = pd.read_csv(valid_manifest).to_dict('records')
    for index, rec in enumerate(m):
        path = dummy_data_dir / rec["sample_id"]
        np.savez(path, kinematics=np.zeros((96, 12)), pose_landmarks=np.zeros((96, 33, 4)), left_hand_landmarks=np.zeros((96, 21, 3)), right_hand_landmarks=np.zeros((96, 21, 3)))
        m[index] = _reverify_record(rec, dummy_data_dir)
    out_path = str(tmp_path / "norm.json")
    fit_fold_normalization(m, get_meta(th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), out_path)
    with open(out_path, "r") as f:
        d = json.load(f)
    assert d["kinematics"]["std"][0] == 1.0

def test_norm_req14_hash_embedding(dummy_data_dir, valid_manifest, tmp_path):
    m = pd.read_csv(valid_manifest).to_dict('records')
    out_path = str(tmp_path / "norm.json")
    fit_fold_normalization(m, get_meta(h="123", th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), out_path)
    with open(out_path, "r") as f:
        d = json.load(f)
    assert d["metadata"]["canonical_provenance_manifest_hash"] == "123"

def test_norm_req15_strict_val_subject_exclusion(dummy_data_dir, valid_manifest, tmp_path):
    from shared.provenance import canonical_provenance_hash
    m = pd.read_csv(valid_manifest).to_dict('records')
    m[0]["subject_id"] = "subject_val"
    m[0]["provenance_hash"] = canonical_provenance_hash(m[0])
    with pytest.raises(ValueError, match="Leakage detected"):
        fit_fold_normalization(m, get_meta(th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "norm.json"))

def test_norm_req16_strict_test_subject_exclusion(dummy_data_dir, valid_manifest, tmp_path):
    from shared.provenance import canonical_provenance_hash
    m = pd.read_csv(valid_manifest).to_dict('records')
    m[0]["subject_id"] = "subject_test"
    m[0]["provenance_hash"] = canonical_provenance_hash(m[0])
    with pytest.raises(ValueError, match="Leakage detected"):
        fit_fold_normalization(m, get_meta(th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "norm.json"))

def test_norm_req17_schema_version_1_1(dummy_data_dir, valid_manifest, tmp_path):
    m = pd.read_csv(valid_manifest).to_dict('records')
    out_path = str(tmp_path / "norm.json")
    fit_fold_normalization(m, get_meta(th=hash_manifest(m)), str(dummy_data_dir), str(dummy_data_dir), out_path)
    with open(out_path, "r") as f:
        d = json.load(f)
    assert d["metadata"]["schema_version"] == "1.1"

def test_norm_req18_nan_computation_error(dummy_data_dir, valid_manifest, tmp_path):
    records = pd.read_csv(valid_manifest).to_dict("records")
    path = dummy_data_dir / records[0]["sample_id"]
    arrays = dict(np.load(path, allow_pickle=False))
    arrays["kinematics"][0, 0] = np.nan
    np.savez(path, **arrays)
    records[0] = _reverify_record(records[0], dummy_data_dir)
    with pytest.raises(ValueError, match="NaN or Inf"):
        fit_fold_normalization(
            records,
            get_meta(th=hash_manifest(records)),
            str(dummy_data_dir),
            str(dummy_data_dir),
            str(tmp_path / "norm.json"),
        )

def test_norm_req19_missing_fold_id(dummy_data_dir, valid_manifest, tmp_path):
    m = pd.read_csv(valid_manifest).to_dict('records')
    meta = {"test_subject": "sub_test", "validation_subjects": ["sub_val"], "canonical_provenance_manifest_hash": "h"}
    with pytest.raises(ValueError, match="Missing fold_id in metadata"):
        fit_fold_normalization(m, meta, str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "n.json"))

def test_norm_req20_missing_prov_hash(dummy_data_dir, valid_manifest, tmp_path):
    m = pd.read_csv(valid_manifest).to_dict('records')
    meta = {"fold_id": "fold_01", "test_subject": "sub_test", "validation_subjects": ["sub_val"]}
    with pytest.raises(ValueError, match="Missing canonical_provenance_manifest_hash"):
        fit_fold_normalization(m, meta, str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "n.json"))

def test_norm_req21_empty_manifest(dummy_data_dir, tmp_path):
    meta = {"fold_id": "fold_01", "test_subject": "sub_test", "validation_subjects": ["sub_val"], "canonical_provenance_manifest_hash": "h"}
    with pytest.raises(ValueError, match="train_manifest is empty"):
        fit_fold_normalization([], meta, str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "n.json"))

def test_norm_req22_duplicate_sample_check(dummy_data_dir, valid_manifest, tmp_path):
    m = pd.read_csv(valid_manifest).to_dict('records')
    m.append(m[0])
    meta = {"fold_id": "fold_01", "test_subject": "sub_test", "validation_subjects": ["sub_val"], "canonical_provenance_manifest_hash": "h", "canonical_train_manifest_hash": hash_manifest(m), "canonical_val_manifest_hash": "vh", "canonical_test_manifest_hash": "th"}
    with pytest.raises(ValueError, match="Duplicate sample_id"):
        fit_fold_normalization(m, meta, str(dummy_data_dir), str(dummy_data_dir), str(tmp_path / "norm.json"))

# ==========================================
# Section 3: Trainer Safeguards (10 assertions)
# ==========================================
def test_train_req23_checkpoint_protocol_1_1(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="protocol_version must be 1.1"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.0", "h1", "h2", "h3", {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req24_checkpoint_missing_model_id(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="model_id is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req25_checkpoint_missing_fold_id(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="fold_id is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req26_checkpoint_missing_prov_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="provenance_hash is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a", "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req27_checkpoint_missing_train_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="train_manifest_hash is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b", "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req28_checkpoint_missing_norm_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="normalization_hash is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "", {0: "a"}, {"a": 1}, "sig", "role")

def test_train_req29_checkpoint_missing_class_mapping(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="class_mapping is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {}, {"a": 1}, "sig", "role")

def test_train_req30_load_strict_fold_mismatch(tmp_path):
    m = DummyModel()
    save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint fold mismatch"):
        load_checkpoint_strict(str(tmp_path/"c.pth"), m, expected_model_id="id", expected_fold_id="f2", expected_protocol="1.1", expected_provenance_hash="a"*64, expected_train_manifest_hash="b"*64, expected_normalization_hash="c"*64, expected_class_mapping={0: "a"}, expected_model_config={"a": 1}, expected_architecture_signature="sig", expected_role="role")

def test_train_req31_load_strict_train_hash_mismatch(tmp_path):
    m = DummyModel()
    save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint train manifest hash mismatch"):
        load_checkpoint_strict(str(tmp_path/"c.pth"), m, expected_model_id="id", expected_fold_id="f1", expected_protocol="1.1", expected_provenance_hash="a"*64, expected_train_manifest_hash="x"*64, expected_normalization_hash="c"*64, expected_class_mapping={0: "a"}, expected_model_config={"a": 1}, expected_architecture_signature="sig", expected_role="role")

def test_train_req32_load_strict_norm_hash_mismatch(tmp_path):
    m = DummyModel()
    save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint normalization hash mismatch"):
        load_checkpoint_strict(str(tmp_path/"c.pth"), m, expected_model_id="id", expected_fold_id="f1", expected_protocol="1.1", expected_provenance_hash="a"*64, expected_train_manifest_hash="b"*64, expected_normalization_hash="x"*64, expected_class_mapping={0: "a"}, expected_model_config={"a": 1}, expected_architecture_signature="sig", expected_role="role")

# ==========================================
# Section 4: Provenance & Hash Infra (11 assertions)
# ==========================================
def test_prov_req33_canonical_hash_allowlist():
    r = build_test_record("a", "b", 1, 1.0, "train", "f", "s", "s", True, "a")
    r["ephemeral_field"] = "x"
    r["data_status_updated_at"] = "y"
    h1 = canonical_provenance_hash(r)
    r["ephemeral_field"] = "z"
    h2 = canonical_provenance_hash(r)
    assert h1 == h2

def test_prov_req34_check_physical_missing_processed(dummy_data_dir):
    record = get_valid_record(dummy_data_dir, 0)
    (dummy_data_dir / record["sample_id"]).unlink()
    ok, message = check_physical_eligibility(
        record, data_dir=str(dummy_data_dir), source_dir=str(dummy_data_dir)
    )
    assert not ok
    assert "processed feature" in message

def test_prov_req35_check_physical_hash_mismatch(dummy_data_dir):
    record = get_valid_record(dummy_data_dir, 0)
    (dummy_data_dir / record["sample_id"]).write_bytes(b"tampered")
    ok, message = check_physical_eligibility(
        record, data_dir=str(dummy_data_dir), source_dir=str(dummy_data_dir)
    )
    assert not ok
    assert "Processed feature hash mismatch" in message


def test_prov_req36_check_physical_success(dummy_data_dir):
    record = get_valid_record(dummy_data_dir, 0)
    ok, message = check_physical_eligibility(
        record,
        data_dir=str(dummy_data_dir),
        source_dir=str(dummy_data_dir),
        verification_key=TEST_VERIFICATION_KEY,
    )
    assert ok, message


def test_prov_req37_hash_manifest_order_independent():
    r1 = build_test_record("a", "b", 1, 1.0, "train", "f", "s", "s", True, "a")
    r2 = build_test_record("c", "d", 1, 1.0, "train", "f", "s", "s", True, "c")
    h1 = hash_manifest([r1, r2])
    h2 = hash_manifest([r2, r1])
    assert h1 == h2

def test_prov_req38_loso_generation_assert_removal():
    import inspect
    from scripts.generate_loso import generate_loso_splits
    src = inspect.getsource(generate_loso_splits)
    assert "assert" not in src

def test_prov_req39_loso_overlap_test_train():
    records = [
        {"sample_id": "1", "subject_id": "01", "source_record_id": "a", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}},
        {"sample_id": "2", "subject_id": "02", "source_record_id": "a", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}},
        {"sample_id": "3", "subject_id": "03", "source_record_id": "c", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}}
    ]
    with pytest.raises(ValueError, match="Duplicate source_record_id"):
        generate_loso_splits(records, expected_subjects=["01", "02", "03"])

def test_prov_req40_loso_exact_subject_count():
    records = [
        {"sample_id": "1", "subject_id": "01", "source_record_id": "a", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}},
    ]
    with pytest.raises(ValueError, match="do not exactly match expected subjects"):
        generate_loso_splits(records, expected_subjects=[f"{i:02d}" for i in range(1, 11)])

def test_prov_req41_loso_duplicate_sample_id():
    records = [
        {"sample_id": "1", "subject_id": "01", "source_record_id": "a", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}},
        {"sample_id": "1", "subject_id": "02", "source_record_id": "b", "data_status": STATUS_REAL_VERIFIED, "extraction_status": "success", "quality_gate_passed": True, "exercise_id": 1, "completion_label": 1.0, "processed_feature_sha256": "a"*64, "source_video_exists": True, "processed_exists": True, "exclusion_reasons": "", "verification_evidence": {"verified_by": "strict_pipeline_v1"}},
    ]
    # They should be excluded due to duplication, triggering exactly 1 subject found exception
    with pytest.raises(ValueError, match="Duplicate sample_id"):
        generate_loso_splits(records, expected_subjects=["01", "02"])
    
def test_prov_req42_dataset_schema_version_1_1(norm_json):
    with open(norm_json) as f:
        schema = json.load(f)
    assert schema["metadata"]["schema_version"] == "1.1"

def test_prov_req43_compute_file_sha256_missing():
    assert compute_file_sha256("nonexistent_file_path.xyz") == ""

# ==========================================
# 4) Training & Evaluation (Req 44-50)
# ==========================================
def test_eval_req44_eval_enforces_manifest_metadata(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    
    # Create test manifest
    test_manifest = tmp_path / "test_manifest.csv"
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(test_manifest, index=False)
    
    with open(norm_json, "r") as f:
        d = json.load(f)
    d["metadata"]["schema_version"] = "1.0"
    with open(norm_json, "w") as f:
        json.dump(d, f)
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, "c"*64, compute_file_sha256(norm_json), {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="schema_version"):
        evaluate_fold(
            fold_id="fold_01",
            model_name="Dummy",
            model=m,
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest=str(test_manifest),
            normalization_json=norm_json,
            checkpoint_path=str(ckpt_path),
            device="cpu"
        )

def test_eval_req45_eval_refuses_train_hash_mismatch(tmp_path, dummy_data_dir, valid_manifest, norm_json):
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    test_manifest = tmp_path / "test_manifest.csv"
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(test_manifest, index=False)
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint train manifest hash mismatch"):
        load_checkpoint_strict(
            filepath=str(ckpt_path),
            model=m,
            expected_model_id="Dummy",
            expected_fold_id="fold_01",
            expected_protocol="1.1",
            expected_provenance_hash="d"*64,
            expected_train_manifest_hash="w"*64,
            expected_normalization_hash="c"*64,
            expected_class_mapping={0: "a"},
            expected_model_config={"a": 1},
            expected_architecture_signature="sig",
            expected_role="role",
            device="cpu"
        )

def test_eval_req46_eval_refuses_norm_hash_mismatch(tmp_path, dummy_data_dir, valid_manifest, norm_json):
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    test_manifest = tmp_path / "test_manifest.csv"
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(test_manifest, index=False)
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint normalization hash mismatch"):
        load_checkpoint_strict(
            filepath=str(ckpt_path),
            model=m,
            expected_model_id="Dummy",
            expected_fold_id="fold_01",
            expected_protocol="1.1",
            expected_provenance_hash="d"*64,
            expected_train_manifest_hash="b"*64,
            expected_normalization_hash="w"*64,
            expected_class_mapping={0: "a"},
            expected_model_config={"a": 1},
            expected_architecture_signature="sig",
            expected_role="role",
            device="cpu"
        )

def test_eval_req47_eval_enforces_no_augmentation(dummy_data_dir, valid_manifest, norm_json, tmp_path):
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    n_hash = compute_file_sha256(norm_json)
    
    df = pd.read_csv(valid_manifest)
    current_train_hash = hash_manifest(df.to_dict('records'))
    
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, current_train_hash, n_hash, {0: "a"}, {"a": 1}, "sig", "role")
    
    with pytest.raises(ValueError, match="Augmentation requested for non-train split"):
        RehabDataset(
            data_dir=str(dummy_data_dir),
            source_dir=str(dummy_data_dir),
            split_manifest_csv=str(valid_manifest),
            split="test",
            normalization_json=norm_json,
            fold_id="fold_01",
            apply_augmentation=True
        )

# ==========================================
# Section 6: Stage 2 Additions (19 assertions)
# ==========================================
def test_checkpoint_req48_missing_model_config(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="model_config is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, None, "sig", "role")

def test_checkpoint_req49_missing_arch_sig(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="architecture_signature is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "", "role")

def test_checkpoint_req50_missing_role(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="checkpoint_role is required"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "")

def test_checkpoint_req51_invalid_prov_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="must be a 64-char SHA256 string"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "short", "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_checkpoint_req52_invalid_train_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="must be a 64-char SHA256 string"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "short", "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_checkpoint_req53_invalid_norm_hash(tmp_path):
    m = DummyModel()
    with pytest.raises(ValueError, match="must be a 64-char SHA256 string"):
        save_checkpoint(m, None, 1, str(tmp_path/"c.pth"), "id", "f1", "1.1", "a"*64, "b"*64, "short", {0: "a"}, {"a": 1}, "sig", "role")

def test_load_req54_model_id_mismatch(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint model_id mismatch"):
        load_checkpoint_strict(p, m, "WRONG", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

def test_load_req55_class_mapping_mismatch(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint class mapping mismatch"):
        load_checkpoint_strict(p, m, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "b"}, {"a": 1}, "sig", "role")

def test_load_req56_model_config_mismatch(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint model config mismatch"):
        load_checkpoint_strict(p, m, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 2}, "sig", "role")

def test_load_req57_arch_sig_mismatch(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint architecture signature mismatch"):
        load_checkpoint_strict(p, m, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "wrong", "role")

def test_load_req58_role_mismatch(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Checkpoint role mismatch"):
        load_checkpoint_strict(p, m, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "wrong")

def test_load_req59_null_hash_disallowed(tmp_path):
    m = DummyModel()
    p = str(tmp_path/"c.pth")
    save_checkpoint(m, None, 1, p, "M1", "F1", "1.1", "a"*64, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")
    with pytest.raises(ValueError, match="Expected hashes cannot be None"):
        load_checkpoint_strict(p, m, "M1", "F1", "1.1", None, "b"*64, "c"*64, {0: "a"}, {"a": 1}, "sig", "role")

from training.model_registry import get_model
def test_registry_req60_unknown_model():
    with pytest.raises(ValueError, match="Unknown model_id"):
        get_model("FakeModel", {})

def test_registry_req61_valid_motionnet():
    model = get_model("bilstm", {"input_dim": 237, "num_exercises": 5, "hidden_size": 8, "num_layers": 1})
    exercise, completion = model(torch.zeros(2, 4, 237))
    assert exercise.shape == (2, 5)
    assert completion.shape == (2, 1)

def test_registry_req62_valid_rehabai():
    model = get_model(
        "RehabMotionNet",
        {
            "num_exercises": 4,
            "use_hand": False,
            "use_kinematic": False,
            "use_contrastive": False,
            "use_mstcn": False,
            "use_attention": False,
        },
    )
    exercise, completion = model(torch.zeros(2, 4, 237))
    assert exercise.shape == (2, 4)
    assert completion.shape == (2, 1)


def test_path_req63_get_checkpoint_path():
    from training.checkpoint_utils import get_checkpoint_path
    path = get_checkpoint_path("/out", "ModelX", "fold_2", "pretrained")
    assert path == os.path.join("/out", "ModelX_fold_2_pretrained.pth")

def test_eval_req64_strict_args_used(tmp_path, dummy_data_dir, valid_manifest, norm_json):
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(valid_manifest, index=False)
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    n_hash = compute_file_sha256(norm_json)
    t_hash = hash_manifest(df.to_dict('records'))
    
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, t_hash, n_hash, {0: "a"}, {"a":1}, "sig", "role")
    
    # Should work
    evaluate_fold(
        fold_id="fold_01",
        model_name="Dummy",
        model=m,
        data_dir=str(dummy_data_dir),
        source_dir=str(dummy_data_dir),
        split_manifest=str(valid_manifest),
        normalization_json=norm_json,
        checkpoint_path=str(ckpt_path),
        device="cpu"
    )
    
def test_eval_req65_strict_args_mismatch(tmp_path, dummy_data_dir, valid_manifest, norm_json):
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(valid_manifest, index=False)
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    n_hash = compute_file_sha256(norm_json)
    t_hash = hash_manifest(df.to_dict('records'))
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, t_hash, n_hash, {0: "a"}, {"a":1}, "sig", "role")
    
    with pytest.raises(ValueError, match="Checkpoint architecture signature mismatch"):
        load_checkpoint_strict(str(ckpt_path), m, "Dummy", "fold_01", "1.1", "d"*64, t_hash, n_hash, {0: "a"}, {"a": 1}, "WRONG_SIG", "role", "cpu")

def test_eval_req66_strict_args_config_mismatch(tmp_path, dummy_data_dir, valid_manifest, norm_json):
    df = pd.read_csv(valid_manifest)
    df["split"] = "test"
    df.to_csv(valid_manifest, index=False)
    m = DummyModel()
    ckpt_path = tmp_path / "model.pth"
    n_hash = compute_file_sha256(norm_json)
    t_hash = hash_manifest(df.to_dict('records'))
    save_checkpoint(m, None, 1, str(ckpt_path), "Dummy", "fold_01", "1.1", "d"*64, t_hash, n_hash, {0: "a"}, {"a":1}, "sig", "role")
    
    with pytest.raises(ValueError, match="Checkpoint model config mismatch"):
        load_checkpoint_strict(str(ckpt_path), m, "Dummy", "fold_01", "1.1", "d"*64, t_hash, n_hash, {0: "a"}, {"a": 999}, "sig", "role", "cpu")
