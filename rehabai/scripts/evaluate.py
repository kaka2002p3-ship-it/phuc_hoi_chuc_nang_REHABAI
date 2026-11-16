import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
import torch
from shared.metrics import accuracy_score, precision_recall_fscore_support
from torch.utils.data import DataLoader

from scripts.generate_loso import hash_manifest
from training.checkpoint_utils import load_checkpoint_strict, compute_file_sha256
from training.datasets.rehab_dataset import RehabDataset
from training.model_registry import get_model

CLASS_MAPPING = {
    0: "Exercise_1",
    1: "Exercise_2",
    2: "Exercise_3",
    3: "Exercise_4",
}


def evaluate_fold(
    fold_id: str,
    model_name: str,
    model: torch.nn.Module,
    data_dir: str,
    source_dir: str,
    split_manifest: str,
    normalization_json: str,
    checkpoint_path: str,
    device: str = "cpu",
    dataset: Optional[RehabDataset] = None,
) -> Dict[str, Any]:
    """Run inference only after a caller has supplied or constructed a strict dataset."""
    del checkpoint_path
    if dataset is None:
        dataset = RehabDataset(
            data_dir=data_dir,
            source_dir=source_dir,
            split_manifest_csv=split_manifest,
            split="test",
            normalization_json=normalization_json,
            fold_id=fold_id,
            apply_augmentation=False,
        )

    loader = DataLoader(dataset, batch_size=32, shuffle=False)
    model.eval()
    model.to(device)
    all_preds = []
    all_targets = []
    all_completion_preds = []
    all_completion_targets = []
    with torch.no_grad():
        for batch in loader:
            features = batch["features"].to(device)
            targets = batch["exercise"].to(device)
            outputs = model(features)
            completion_logits = None
            if hasattr(outputs, "logits"):
                logits = outputs.logits
            elif isinstance(outputs, tuple):
                logits = outputs[0]
                if len(outputs) > 1:
                    completion_logits = outputs[1]
            else:
                logits = outputs
            all_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
            all_targets.extend(targets.cpu().numpy())
            if completion_logits is not None and "completion" in batch:
                all_completion_preds.extend((torch.sigmoid(completion_logits).reshape(-1) >= 0.5).long().cpu().numpy())
                all_completion_targets.extend(batch["completion"].reshape(-1).long().cpu().numpy())

    labels = list(CLASS_MAPPING)
    acc = accuracy_score(all_targets, all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_targets,
        all_preds,
        average="macro",
        zero_division=0,
        labels=labels,
    )
    per_class_precision, per_class_recall, per_class_f1, per_class_support = precision_recall_fscore_support(
        all_targets,
        all_preds,
        average=None,
        zero_division=0,
        labels=labels,
    )
    support_total = int(np.sum(per_class_support))
    weighted_f1 = (
        float(np.sum(per_class_f1 * per_class_support) / support_total)
        if support_total else 0.0
    )
    confusion = np.zeros((len(labels), len(labels)), dtype=int)
    for target, prediction in zip(all_targets, all_preds):
        if int(target) in labels and int(prediction) in labels:
            confusion[int(target), int(prediction)] += 1
    result = {
        "fold_id": fold_id,
        "model_name": model_name,
        "accuracy": float(acc),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1),
        "f1_weighted": weighted_f1,
        "per_class": {
            str(label): {
                "precision": float(per_class_precision[index]),
                "recall": float(per_class_recall[index]),
                "f1": float(per_class_f1[index]),
                "support": int(per_class_support[index]),
            }
            for index, label in enumerate(labels)
        },
        "confusion_matrix": confusion.tolist(),
        "sample_count": len(all_targets),
        "observed_classes": sorted({int(value) for value in all_targets}),
        "expected_classes": labels,
        "class_coverage_complete": set(all_targets) == set(labels),
        "task_evaluated": "exercise_classification",
        "task_omitted": None if all_completion_targets else "completion_head_not_available",
    }
    if all_completion_targets:
        cp, cr, cf1, _ = precision_recall_fscore_support(
            all_completion_targets, all_completion_preds,
            average="macro", zero_division=0, labels=[0, 1],
        )
        result.update({
            "completion_accuracy": float(accuracy_score(all_completion_targets, all_completion_preds)),
            "completion_precision_macro": float(cp),
            "completion_recall_macro": float(cr),
            "completion_f1_macro": float(cf1),
            "completion_sample_count": len(all_completion_targets),
            "completion_observed_classes": sorted({int(value) for value in all_completion_targets}),
            "completion_confusion_matrix": [
                [
                    int(sum(
                        int(target) == actual and int(prediction) == predicted
                        for target, prediction in zip(all_completion_targets, all_completion_preds)
                    ))
                    for predicted in (0, 1)
                ]
                for actual in (0, 1)
            ],
        })
    return result


def _required_job_value(job: Dict[str, Any], name: str) -> Any:
    value = job.get(name)
    if value is None or value == "":
        raise ValueError(f"Evaluation job missing required field: {name}")
    return value


def _normalized_class_mapping(value: Any) -> Dict[int, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("expected_class_mapping must be a non-empty object")
    mapping = {int(key): str(label) for key, label in value.items()}
    if mapping != CLASS_MAPPING:
        raise ValueError(f"Evaluation class mapping must equal the canonical mapping: {CLASS_MAPPING}")
    return mapping


def _preflight_job(job: Dict[str, Any]) -> Dict[str, Any]:
    fold_id = str(_required_job_value(job, "fold_id"))
    model_name = str(_required_job_value(job, "model_name"))
    data_dir = str(_required_job_value(job, "data_dir"))
    source_dir = str(_required_job_value(job, "source_dir"))
    split_manifest = str(_required_job_value(job, "split_manifest"))
    normalization_json = str(_required_job_value(job, "normalization_json"))
    checkpoint_path = str(_required_job_value(job, "checkpoint_path"))
    fold_metadata_path = str(_required_job_value(job, "fold_metadata_path"))
    expected_model_config = _required_job_value(job, "expected_model_config")
    expected_architecture_signature = str(_required_job_value(job, "expected_architecture_signature"))
    expected_class_mapping = _normalized_class_mapping(_required_job_value(job, "expected_class_mapping"))
    expected_role = str(job.get("expected_role", "supervised_model"))
    expected_protocol = str(job.get("expected_protocol", "1.1"))

    for label, path in {
        "data_dir": data_dir,
        "source_dir": source_dir,
        "split_manifest": split_manifest,
        "normalization_json": normalization_json,
        "checkpoint_path": checkpoint_path,
        "fold_metadata_path": fold_metadata_path,
    }.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"{label} not found: {path}")

    with open(fold_metadata_path, "r", encoding="utf-8") as handle:
        fold_metadata = json.load(handle)
    if str(fold_metadata.get("fold_id")) != fold_id:
        raise ValueError(
            f"Fold metadata mismatch: expected {fold_id}, got {fold_metadata.get('fold_id')}"
        )

    required_hashes = {
        name: fold_metadata.get(name)
        for name in (
            "canonical_provenance_manifest_hash",
            "canonical_train_manifest_hash",
            "canonical_val_manifest_hash",
            "canonical_test_manifest_hash",
        )
    }
    missing = [name for name, value in required_hashes.items() if not value]
    if missing:
        raise ValueError(f"Missing canonical hashes in fold metadata: {missing}")

    manifest_records = pd.read_csv(split_manifest, dtype={"subject_id": str}).to_dict("records")
    if not manifest_records or any(str(record.get("split")) != "test" for record in manifest_records):
        raise ValueError("Evaluation manifest must be non-empty and contain only split=test records")
    actual_test_hash = hash_manifest(manifest_records)
    if actual_test_hash != required_hashes["canonical_test_manifest_hash"]:
        raise ValueError(
            f"Test manifest hash mismatch. Expected {required_hashes['canonical_test_manifest_hash']}, "
            f"got {actual_test_hash}"
        )

    with open(normalization_json, "r", encoding="utf-8") as handle:
        norm = json.load(handle)
    norm_meta = norm.get("metadata", {})
    expected_norm_meta = {
        "schema_version": "1.1",
        "fold_id": fold_id,
        **required_hashes,
    }
    for name, expected in expected_norm_meta.items():
        if str(norm_meta.get(name)) != str(expected):
            raise ValueError(
                f"Normalization metadata mismatch for {name}: expected {expected}, got {norm_meta.get(name)}"
            )

    model = get_model(model_name, config=expected_model_config)
    checkpoint = load_checkpoint_strict(
        filepath=checkpoint_path,
        model=model,
        expected_model_id=model_name,
        expected_fold_id=fold_id,
        expected_protocol=expected_protocol,
        expected_provenance_hash=required_hashes["canonical_provenance_manifest_hash"],
        expected_train_manifest_hash=required_hashes["canonical_train_manifest_hash"],
        expected_normalization_hash=compute_file_sha256(normalization_json),
        expected_class_mapping=expected_class_mapping,
        expected_model_config=expected_model_config,
        expected_architecture_signature=expected_architecture_signature,
        expected_role=expected_role,
        device="cpu",
    )

    # Constructing every dataset in preflight performs provenance, physical-file,
    # split, fold, normalization and exact-shape checks before any inference.
    dataset = RehabDataset(
        data_dir=data_dir,
        source_dir=source_dir,
        split_manifest_csv=split_manifest,
        split="test",
        normalization_json=normalization_json,
        fold_id=fold_id,
        apply_augmentation=False,
    )
    prepared = dict(job)
    prepared.update(
        {
            "fold_id": fold_id,
            "model_name": model_name,
            "preflighted_model": model,
            "preflighted_dataset": dataset,
            "checkpoint_metadata": checkpoint,
        }
    )
    return prepared


def _atomic_write_json(output_file: str, payload: Any) -> None:
    target = Path(output_file).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, indent=4)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def run_evaluation(config_path: str):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    jobs = config.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Evaluation config missing non-empty jobs array")

    # Do not move this work into the inference loop: all jobs must be completely
    # preflighted before the first model sees a batch.
    prepared_jobs = [_preflight_job(job) for job in jobs]

    metrics = []
    for job in prepared_jobs:
        result = evaluate_fold(
            fold_id=job["fold_id"],
            model_name=job["model_name"],
            model=job["preflighted_model"],
            data_dir=job["data_dir"],
            source_dir=job["source_dir"],
            split_manifest=job["split_manifest"],
            normalization_json=job["normalization_json"],
            checkpoint_path=job["checkpoint_path"],
            device="cuda" if torch.cuda.is_available() else "cpu",
            dataset=job["preflighted_dataset"],
        )
        result["metadata"] = job["checkpoint_metadata"]["metadata"]
        metrics.append(result)

    _atomic_write_json(config.get("output_file", "results.json"), metrics)
    return metrics


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python evaluate.py <config.json>", file=sys.stderr)
        sys.exit(1)
    try:
        run_evaluation(sys.argv[1])
    except Exception as exc:
        print(f"EVALUATION FAILED DUE TO CONSTRAINT VIOLATION: {exc}", file=sys.stderr)
        sys.exit(1)
    print("Evaluation completed successfully.")
