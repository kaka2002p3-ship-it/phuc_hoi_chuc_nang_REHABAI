import os
import json
import argparse
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from shared.provenance import check_physical_eligibility
from scripts.generate_loso import hash_manifest

def fit_fold_normalization(
    train_manifest: List[Dict[str, Any]], 
    fold_metadata: Dict[str, Any],
    processed_dir: str, 
    source_dir: str,
    output_path: str
):
    """
    Fit normalization schema strictly on TRAIN samples for a specific fold.
    Enforces research invariants to prevent validation/test leakage.
    """
    
    if not train_manifest:
        raise ValueError("train_manifest is empty")
        
    fold_id = fold_metadata.get("fold_id")
    if not fold_id:
        raise ValueError("Missing fold_id in metadata")
        
    test_subject = fold_metadata.get("test_subject")
    val_subjects = fold_metadata.get("validation_subjects", [])
    expected_prov_hash = fold_metadata.get("canonical_provenance_manifest_hash")
    expected_train_hash = fold_metadata.get("canonical_train_manifest_hash")
    expected_val_hash = fold_metadata.get("canonical_val_manifest_hash")
    expected_test_hash = fold_metadata.get("canonical_test_manifest_hash")
    
    if not expected_prov_hash:
         raise ValueError("Missing canonical_provenance_manifest_hash in fold metadata")
    if not expected_train_hash:
         raise ValueError("Missing canonical_train_manifest_hash in fold metadata")
    if not expected_val_hash:
         raise ValueError("Missing canonical_val_manifest_hash in fold metadata")
    if not expected_test_hash:
         raise ValueError("Missing canonical_test_manifest_hash in fold metadata")
    
    if not source_dir:
         raise ValueError("source_dir is required in strict research mode")
    if not processed_dir:
         raise ValueError("processed_dir is required in strict research mode")
         
    # Optional check: Ideally the entire fold manifest has the expected_prov_hash,
    # but since we only have train_manifest here, we calculate its hash to store.
    
    # 1. Validation phase
    seen_samples = set()
    for record in train_manifest:
        # Check fold and split before expensive physical I/O.
        if record.get("fold_id") != fold_id:
            raise ValueError(f"Record {record.get('sample_id')} has wrong fold_id: {record.get('fold_id')} != {fold_id}")
            
        if record.get("split") != "train":
            raise ValueError(f"Record {record.get('sample_id')} has wrong split: {record.get('split')} != train")
            
        # Check leakage
        subj = str(record.get("subject_id")).zfill(2)
        if subj == str(test_subject).zfill(2) or subj in [str(s).zfill(2) for s in val_subjects]:
            raise ValueError(f"Leakage detected! Record {record.get('sample_id')} belongs to val/test subject {subj}")
            
        # Check duplicates
        sample_id = record.get("sample_id")
        if sample_id in seen_samples:
            raise ValueError(f"Duplicate sample_id detected in train manifest: {sample_id}")
        seen_samples.add(sample_id)

        ok, reason = check_physical_eligibility(
            record, data_dir=processed_dir, source_dir=source_dir
        )
        if not ok:
            raise ValueError(f"Ineligible record in normalization fit: {sample_id} - {reason}")
        
    # Generate train_manifest hash
    train_manifest_hash = hash_manifest(train_manifest)
    if train_manifest_hash != expected_train_hash:
        raise ValueError(f"Train manifest hash mismatch in normalization. Expected {expected_train_hash}, got {train_manifest_hash}")
        
    all_kinematics = []
    expected_dim = -1
    
    train_subjects = sorted(list(set([str(r["subject_id"]).zfill(2) for r in train_manifest])))
    
    for record in train_manifest:
        file_path = os.path.join(processed_dir, record["sample_id"])
        
        try:
            data = np.load(file_path, allow_pickle=False)
            if "kinematics" not in data:
                raise KeyError(f"'kinematics' key not found in {file_path}")
                
            kinematics = data["kinematics"]
            if not isinstance(kinematics, np.ndarray):
                raise ValueError(f"Kinematics is not a numpy array in {file_path}")
                
            if np.isnan(kinematics).any() or np.isinf(kinematics).any():
                raise ValueError(f"NaN or Inf features found in {file_path}")
                
            if len(kinematics.shape) != 2:
                raise ValueError(f"Expected 2D array (frames, features) but got {kinematics.shape} in {file_path}")
                
            if expected_dim == -1:
                expected_dim = kinematics.shape[1]
            elif kinematics.shape[1] != expected_dim:
                raise ValueError(f"Feature dimension mismatch: expected {expected_dim}, got {kinematics.shape[1]} in {file_path}")
                
            all_kinematics.append(kinematics)
        except Exception as e:
            raise ValueError(f"Error loading {file_path}: {e}")
            
    if len(all_kinematics) == 0:
         raise ValueError("No valid kinematic data found.")
         
    concatenated_kinematics = np.concatenate(all_kinematics, axis=0) # shape: (TotalFrames, Features)
    mean = np.nanmean(concatenated_kinematics, axis=0)
    std = np.nanstd(concatenated_kinematics, axis=0)
    
    if np.isnan(mean).any() or np.isnan(std).any():
        raise ValueError("NaNs present in computed mean/std across the training set.")
    
    
    # Replace near-zero std with 1.0 safely
    std = np.where(std < 1e-5, 1.0, std)
    
    schema = {
        "metadata": {
            "schema_version": "1.1",
            "fold_id": fold_id,
            "train_subjects": train_subjects,
            "canonical_provenance_manifest_hash": expected_prov_hash,
            "canonical_train_manifest_hash": train_manifest_hash,
            "canonical_val_manifest_hash": expected_val_hash,
            "canonical_test_manifest_hash": expected_test_hash,
            "feature_dimension": expected_dim,
            "sample_count": len(train_manifest),
            "frame_count": int(concatenated_kinematics.shape[0]),
            "near_zero_variance_handling": "replace_with_1.0"
        },
        "kinematics": {
            "mean": mean.tolist(),
            "std": std.tolist()
        }
    }
    
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(schema, handle, indent=4)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        
    return schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Fit train-only normalization for one strict LOSO fold.")
    parser.add_argument("--train-manifest", required=True)
    parser.add_argument("--fold-metadata", required=True)
    parser.add_argument("--processed-dir", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    records = pd.read_csv(args.train_manifest, dtype={"subject_id": str}).to_dict("records")
    with open(args.fold_metadata, "r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    schema = fit_fold_normalization(
        records, metadata, args.processed_dir, args.source_dir, args.output
    )
    print(
        f"Normalization written to {Path(args.output).resolve()} "
        f"from {schema['metadata']['sample_count']} train-only samples."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
