import os
import json
import pytest
import tempfile
import torch
import pandas as pd
from pathlib import Path

from training.datasets.rehab_dataset import RehabDataset
from training.normalization import fit_fold_normalization
from shared.provenance import compute_sha256, build_provenance_record, canonical_provenance_hash, verify_and_grant_real_verified, check_eligibility, STATUS_REAL_VERIFIED, VERIFICATION_KEY_ENV
from training.checkpoint_utils import save_checkpoint, load_checkpoint_strict
from scripts.generate_loso import hash_manifest
from scripts.evaluate import run_evaluation

class MockModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(237, 4)
    def forward(self, x):
        # x is (B, T, 237) -> mean pool -> linear
        return self.linear(x.mean(dim=1))

@pytest.fixture(autouse=True)
def verification_authority(monkeypatch):
    monkeypatch.setenv(VERIFICATION_KEY_ENV, "strict-pipeline-test-key-at-least-32-bytes")

@pytest.fixture
def workspace():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

def test_provenance_and_eligibility(workspace):
    # 1. Create source and processed files
    source_file = workspace / "src.mp4"
    source_file.write_bytes(b"dummy source")
    processed_file = workspace / "proc.npy"
    processed_file.write_bytes(b"dummy processed")
    
    src_hash = compute_sha256(str(source_file))
    proc_hash = compute_sha256(str(processed_file))
    
    # 2. Build record
    record = build_provenance_record(
        source_video_path=str(source_file),
        subject_id="P01",
        exercise_id=1,
        completion_label=1.0,
        extraction_status="success",
        extractor_version="v1.0.0",
        interim_path=None,
        processed_path=str(processed_file),
        quality_gate_passed=True,
        compute_hash=True
    )
    
    # Record should be REAL_CANDIDATE
    assert record["data_status"] == "REAL_CANDIDATE"
    
    # 3. Verify and grant REAL_VERIFIED
    # Need absolute paths for verify
    record = verify_and_grant_real_verified(record, str(workspace), str(workspace))
    assert record["data_status"] == STATUS_REAL_VERIFIED
    
    # 4. Check eligibility
    is_eligible, elig_reason = check_eligibility(record)
    assert is_eligible, f"Failed eligibility: {elig_reason}"
    
    # Tampering test
    tampered_record = dict(record)
    tampered_record["source_video_sha256"] = "badhash"
    # Should fail eligibility
    is_eligible_t, _ = check_eligibility(tampered_record)
    assert not is_eligible_t

def test_normalization_schema(workspace):
    # Setup folders
    source_dir = workspace / "source"
    source_dir.mkdir()
    data_dir = workspace / "processed"
    data_dir.mkdir()
    
    # Create sample file
    import numpy as np
    proc_file = data_dir / "vid1.npz"
    np.savez(proc_file, kinematics=np.random.randn(10, 12).astype(np.float32), pose_landmarks=np.random.randn(10, 33, 4).astype(np.float32), left_hand_landmarks=np.random.randn(10, 21, 3).astype(np.float32), right_hand_landmarks=np.random.randn(10, 21, 3).astype(np.float32))
    src_file = source_dir / "vid1.mp4"
    src_file.write_bytes(b"dummy")
    
    # Create train manifest
    record = build_provenance_record(
        source_video_path=str(src_file),
        subject_id="P01",
        exercise_id=1,
        completion_label=1.0,
        extraction_status="success",
        extractor_version="v1.0.0",
        processed_path=str(proc_file),
        quality_gate_passed=True,
        compute_hash=True
    )
    record = verify_and_grant_real_verified(record, str(source_dir), str(data_dir))
    record["fold_id"] = "fold_0"
    record["split"] = "train"
    train_manifest = [record]
    
    metadata = {
        "fold_id": "fold_0",
        "canonical_provenance_manifest_hash": "prov_hash",
        "canonical_train_manifest_hash": hash_manifest(train_manifest),
        "canonical_val_manifest_hash": "val_hash",
        "canonical_test_manifest_hash": "test_hash"
    }
    
    norm_json = workspace / "norm.json"
    fit_fold_normalization(
        train_manifest=train_manifest,
        fold_metadata=metadata,
        processed_dir=str(data_dir),
        source_dir=str(source_dir),
        output_path=str(norm_json)
    )
    
    with open(norm_json, "r") as f:
        data = json.load(f)
        
    assert data["metadata"]["schema_version"] == "1.1"
    assert data["metadata"]["canonical_train_manifest_hash"] == hash_manifest(train_manifest)
    
def test_rehab_dataset_strictness(workspace):
    # Setup folders
    source_dir = workspace / "source"
    source_dir.mkdir()
    data_dir = workspace / "processed"
    data_dir.mkdir()
    
    # Create files
    src_file = source_dir / "vid1.mp4"
    src_file.write_bytes(b"vid1")
    
    # Using numpy to save
    import numpy as np
    proc_file = data_dir / "vid1.npz"
    np.savez(
        proc_file,
        kinematics=np.random.randn(10, 12).astype(np.float32),
        pose_landmarks=np.random.randn(10, 33, 4).astype(np.float32),
        left_hand_landmarks=np.random.randn(10, 21, 3).astype(np.float32),
        right_hand_landmarks=np.random.randn(10, 21, 3).astype(np.float32),
        label=1,
    )
    
    record = build_provenance_record(
        source_video_path=str(src_file),
        subject_id="P01",
        exercise_id=1,
        completion_label=1.0,
        extraction_status="success",
        extractor_version="v1.0.0",
        processed_path=str(proc_file),
        quality_gate_passed=True,
        compute_hash=True
    )
    record = verify_and_grant_real_verified(record, str(source_dir), str(data_dir))
    record["fold_id"] = "fold_0"
    record["split"] = "train"
    
    # Write provenance
    prov_csv = workspace / "provenance.csv"
    pd.DataFrame([record]).to_csv(prov_csv, index=False)
    
    # Write train manifest
    train_manifest = workspace / "train.csv"
    pd.DataFrame([record]).to_csv(train_manifest, index=False)
    
    # Read back to account for pandas stringification/types before hashing
    train_records = pd.read_csv(train_manifest).to_dict('records')
    train_hash = hash_manifest(train_records)
    
    # Write metadata and norm
    metadata = {
        "fold_id": "fold_0",
        "canonical_provenance_manifest_hash": compute_sha256(str(prov_csv)),
        "canonical_train_manifest_hash": train_hash,
        "canonical_val_manifest_hash": "val_hash",
        "canonical_test_manifest_hash": "test_hash"
    }
    
    norm_json = workspace / "norm.json"
    fit_fold_normalization(train_records, metadata, str(data_dir), str(source_dir), str(norm_json))
    
    # Dataset should load
    ds = RehabDataset(
        data_dir=str(data_dir),
        source_dir=str(source_dir),
        split_manifest_csv=str(train_manifest),
        split="train",
        normalization_json=str(norm_json),
        fold_id="fold_0",
        apply_augmentation=False
    )
    
    assert len(ds) == 1
    
def test_checkpoint_strict_loader(workspace):
    # Prepare dependencies
    model = MockModel()
    chk_path = workspace / "checkpoint.pth"
    
    # Save valid checkpoint
    valid_hash = "a" * 64
    save_checkpoint(
        model=model,
        optimizer=None,
        epoch=1,
        filepath=str(chk_path),
        model_id="MockModel",
        fold_id="fold_0",
        protocol_version="1.1",
        provenance_hash=valid_hash,
        train_manifest_hash=valid_hash,
        normalization_hash=valid_hash,
        class_mapping={0: "Exercise_1"},
        model_config={"num_classes": 4},
        architecture_signature="sig_123",
        checkpoint_role="supervised_model",
        val_loss=0.1,
        val_acc=0.9
    )
    
    # Valid strict load
    checkpoint_dict = load_checkpoint_strict(
        filepath=str(chk_path),
        model=model,
        expected_model_id="MockModel",
        expected_fold_id="fold_0",
        expected_protocol="1.1",
        expected_provenance_hash=valid_hash,
        expected_train_manifest_hash=valid_hash,
        expected_normalization_hash=valid_hash,
        expected_class_mapping={0: "Exercise_1"},
        expected_model_config={"num_classes": 4},
        expected_architecture_signature="sig_123",
        expected_role="supervised_model",
        device="cpu"
    )
    assert checkpoint_dict["metadata"]["fold_id"] == "fold_0"
    
    # Invalid strict load (mismatch hash)
    with pytest.raises(ValueError):
        load_checkpoint_strict(
            filepath=str(chk_path),
            model=model,
            expected_model_id="MockModel",
            expected_fold_id="fold_0",
            expected_protocol="1.1",
            expected_provenance_hash="b" * 64, # Mismatch
            expected_train_manifest_hash=valid_hash,
            expected_normalization_hash=valid_hash,
            expected_class_mapping={0: "Exercise_1"},
            expected_model_config={"num_classes": 4},
            expected_architecture_signature="sig_123",
            expected_role="supervised_model",
            device="cpu"
        )
