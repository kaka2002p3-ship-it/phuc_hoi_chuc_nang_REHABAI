import os
import json
import csv
import hashlib
import argparse
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any

from shared.provenance import filter_or_reject_manifest, canonical_provenance_hash

def hash_manifest(records: List[Dict[str, Any]]) -> str:
    """Generate a deterministic hash from a list of records."""
    # Ensure independent of CSV field order
    sorted_records = sorted([canonical_provenance_hash(r) for r in records])
    return hashlib.sha256("".join(sorted_records).encode('utf-8')).hexdigest()

def generate_loso_splits(
    input_records: List[Dict[str, Any]],
    expected_subjects: List[str],
    deterministic_seed: int = 42,
    preferred_validation_subjects: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Generate LOSO folds from input records.
    Filters out ineligible records strictly and enforces fold generation invariants.
    """
    if not expected_subjects or len(expected_subjects) == 0:
        raise ValueError("Must provide an exact non-empty list of expected subjects.")
    expected_subjects = [str(s).zfill(2) for s in expected_subjects]

    sample_ids = [str(record.get("sample_id")) for record in input_records]
    source_ids = [str(record.get("source_record_id")) for record in input_records]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Duplicate sample_id found in input provenance manifest")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate source_record_id found in input provenance manifest")

    eligible_records, excluded_records = filter_or_reject_manifest(input_records)
    
    # Normalize subjects and sort deterministically
    subjects = sorted(list(set([str(r["subject_id"]).zfill(2) for r in eligible_records])))
    
    if set(subjects) != set(expected_subjects):
        raise ValueError(f"Eligible subjects {subjects} do not exactly match expected subjects {expected_subjects}")
        
    folds = {}
    coverage = {
        subject: sorted({int(float(r["exercise_id"])) for r in eligible_records if str(r["subject_id"]).zfill(2) == subject})
        for subject in subjects
    }
    complete_subjects = [subject for subject in subjects if coverage[subject] == [1, 2, 3, 4]]
    preferred = [str(subject).zfill(2) for subject in (preferred_validation_subjects or complete_subjects)]
    preferred = [subject for subject in preferred if subject in subjects and coverage[subject] == [1, 2, 3, 4]]
    
    for i, test_subject in enumerate(subjects):
        fold_id = f"fold_{str(i+1).zfill(2)}"
        
        # Validation remains subject-disjoint, but a full four-class subject is
        # preferred.  This avoids early stopping on one-class subjects 07-10 in
        # the Upper Limb dataset.  Fall back deterministically only when the
        # supplied dataset has no full-coverage subject (e.g. minimal fixtures).
        validation_pool = [subject for subject in preferred if subject != test_subject]
        if validation_pool:
            val_subject = validation_pool[i % len(validation_pool)]
        else:
            val_subject = subjects[(i + 1) % len(subjects)]
        
        train_subjects = [s for s in subjects if s not in (test_subject, val_subject)]
        
        # Verify subjects are disjoint
        if test_subject in train_subjects:
            raise ValueError(f"Fold {fold_id}: test_subject {test_subject} found in train_subjects")
        if val_subject in train_subjects:
            raise ValueError(f"Fold {fold_id}: val_subject {val_subject} found in train_subjects")
        if test_subject == val_subject:
             raise ValueError(f"Fold {fold_id}: test_subject and val_subject are identical: {test_subject}")
        
        # Partition records and explicitly add fold_id and split
        test_records = []
        val_records = []
        train_records = []
        
        for r in eligible_records:
            record_copy = r.copy()
            record_copy["fold_id"] = fold_id
            subj = str(r["subject_id"]).zfill(2)
            if subj == test_subject:
                record_copy["split"] = "test"
                test_records.append(record_copy)
            elif subj == val_subject:
                record_copy["split"] = "val"
                val_records.append(record_copy)
            elif subj in train_subjects:
                record_copy["split"] = "train"
                train_records.append(record_copy)
            else:
                raise ValueError(f"Record {r.get('sample_id')} does not map to train/val/test in fold {fold_id}")
                
        # Check source video and sample overlap thoroughly across train/val/test
        test_vids = set(r.get("source_record_id") for r in test_records)
        val_vids = set(r.get("source_record_id") for r in val_records)
        train_vids = set(r.get("source_record_id") for r in train_records)
        
        test_samples = set(r.get("sample_id") for r in test_records)
        val_samples = set(r.get("sample_id") for r in val_records)
        train_samples = set(r.get("sample_id") for r in train_records)
        
        test_hashes = set(r.get("source_video_sha256") for r in test_records)
        val_hashes = set(r.get("source_video_sha256") for r in val_records)
        train_hashes = set(r.get("source_video_sha256") for r in train_records)
        
        # Helper to check disjoint sets
        def check_disjoint(s1, s2, err_msg):
            if len(s1.intersection(s2)) > 0:
                raise ValueError(err_msg)
                
        check_disjoint(test_vids, train_vids, "Test and Train source_record_id overlap")
        check_disjoint(val_vids, train_vids, "Val and Train source_record_id overlap")
        check_disjoint(test_vids, val_vids, "Test and Val source_record_id overlap")
        
        check_disjoint(test_samples, train_samples, "Test and Train sample_id overlap")
        check_disjoint(val_samples, train_samples, "Val and Train sample_id overlap")
        check_disjoint(test_samples, val_samples, "Test and Val sample_id overlap")
        
        check_disjoint(test_hashes, train_hashes, "Test and Train source_video_sha256 overlap")
        check_disjoint(val_hashes, train_hashes, "Val and Train source_video_sha256 overlap")
        check_disjoint(test_hashes, val_hashes, "Test and Val source_video_sha256 overlap")
            
        # Manifest hash
        fold_manifest_hash = hash_manifest(eligible_records)
        train_manifest_hash = hash_manifest(train_records)
        val_manifest_hash = hash_manifest(val_records)
        test_manifest_hash = hash_manifest(test_records)
        
        folds[fold_id] = {
            "metadata": {
                "protocol_version": "1.1",
                "fold_id": fold_id,
                "seed": deterministic_seed,
                "test_subject": test_subject,
                "validation_subjects": [val_subject],
                "train_subjects": train_subjects,
                "input_record_count": len(input_records),
                "eligible_count": len(eligible_records),
                "excluded_count": len(excluded_records),
                "per_split_sample_count": {
                    "train": len(train_records),
                    "val": len(val_records),
                    "test": len(test_records)
                },
                "exercise_coverage": {
                    "train": sorted({int(float(r["exercise_id"])) for r in train_records}),
                    "val": sorted({int(float(r["exercise_id"])) for r in val_records}),
                    "test": sorted({int(float(r["exercise_id"])) for r in test_records}),
                },
                "test_class_coverage_note": (
                    "complete" if coverage[test_subject] == [1, 2, 3, 4]
                    else "intrinsically_partial_for_this_subject"
                ),
                "canonical_provenance_manifest_hash": fold_manifest_hash,
                "canonical_train_manifest_hash": train_manifest_hash,
                "canonical_val_manifest_hash": val_manifest_hash,
                "canonical_test_manifest_hash": test_manifest_hash
            },
            "train_manifest": train_records,
            "val_manifest": val_records,
            "test_manifest": test_records,
            "excluded_manifest": excluded_records
        }
        
    return folds

def save_folds(folds: Dict[str, Any], output_dir: str):
    """Save folds to disk deterministically."""
    for fold_id, fold_data in folds.items():
        fold_dir = os.path.join(output_dir, fold_id)
        os.makedirs(fold_dir, exist_ok=True)
        
        # Save metadata
        with open(os.path.join(fold_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(fold_data["metadata"], f, indent=4, sort_keys=True)
            
        for split, records in [
            ("train", fold_data["train_manifest"]), 
            ("val", fold_data["val_manifest"]), 
            ("test", fold_data["test_manifest"]),
            ("excluded", fold_data.get("excluded_manifest", []))
        ]:
            if not records: continue
            
            # Use deterministic sorting for rows based on sample_id
            sorted_records = sorted(records, key=lambda x: str(x.get("sample_id", "")))
            
            # Extract all possible keys
            keys = []
            for r in sorted_records:
                for k in r.keys():
                    if k not in keys:
                        keys.append(k)
                        
            with open(os.path.join(fold_dir, f"{split}_manifest.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(sorted_records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic true LOSO folds from a signed manifest.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="data/stage3_real/loso")
    parser.add_argument("--subjects", nargs="+", default=[f"{i:02d}" for i in range(1, 11)])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_path = Path(args.input_csv).resolve(strict=True)
    output_dir = Path(args.output_dir).resolve()
    records = pd.read_csv(input_path, dtype={"subject_id": str}).to_dict("records")
    folds = generate_loso_splits(records, args.subjects, deterministic_seed=args.seed)
    save_folds(folds, str(output_dir))
    print(f"Generated {len(folds)} strict LOSO folds in {output_dir}")
    for fold_id, fold in folds.items():
        meta = fold["metadata"]
        counts = meta["per_split_sample_count"]
        print(
            f"{fold_id}: test={meta['test_subject']}, val={meta['validation_subjects'][0]}, "
            f"train={counts['train']}, val_n={counts['val']}, test_n={counts['test']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
