"""Create validated real-data features and unsigned provenance candidates for Stage 3."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from shared.preprocessing.kinematics import get_kinematic_features
from shared.preprocessing.normalization import normalize_landmarks
from shared.provenance import (
    STATUS_REAL_CANDIDATE,
    build_provenance_record,
    canonical_provenance_hash,
    compute_sha256,
)
from training.datasets.feature_validation import validate_feature_arrays


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = PROJECT_ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED" / "01_Upper_Limb_Stroke"
DEFAULT_INTERIM_DIR = PROJECT_ROOT / "data" / "stage3_real" / "interim" / "keypoints"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "stage3_real" / "processed" / "keypoints"
DEFAULT_QUALITY_LOG = PROJECT_ROOT / "data" / "stage3_real" / "indexes" / "extraction_quality.csv"
DEFAULT_CANDIDATES = PROJECT_ROOT / "data" / "stage3_real" / "indexes" / "provenance_candidates.csv"
DEFAULT_ERRORS = PROJECT_ROOT / "data" / "stage3_real" / "indexes" / "processing_errors.csv"
PROCESSOR_VERSION = "stage3-real-v1"
RAW_KEYS = (
    "pose_landmarks", "left_hand_landmarks", "right_hand_landmarks",
    "timestamps", "frame_indices",
)


def atomic_save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        pd.DataFrame(records).to_csv(temp_name, index=False)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def completion_to_float(value: Any) -> float:
    normalized = str(value).strip().lower()
    if normalized in {"complete", "1", "1.0", "true"}:
        return 1.0
    if normalized in {"incomplete", "0", "0.0", "false"}:
        return 0.0
    raise ValueError(f"Unsupported completion_label: {value!r}")


def validate_raw(data: Any, path: Path) -> None:
    for key in RAW_KEYS:
        if key not in data:
            raise KeyError(f"Raw extraction missing {key}: {path}")
    pose = data["pose_landmarks"]
    left = data["left_hand_landmarks"]
    right = data["right_hand_landmarks"]
    timestamps = data["timestamps"]
    indices = data["frame_indices"]
    if pose.ndim != 3 or tuple(pose.shape[1:]) != (33, 4):
        raise ValueError(f"Invalid raw pose shape in {path}: {pose.shape}")
    if left.ndim != 3 or tuple(left.shape[1:]) != (21, 3):
        raise ValueError(f"Invalid raw left-hand shape in {path}: {left.shape}")
    if right.ndim != 3 or tuple(right.shape[1:]) != (21, 3):
        raise ValueError(f"Invalid raw right-hand shape in {path}: {right.shape}")
    frame_count = pose.shape[0]
    if frame_count <= 0 or left.shape[0] != frame_count or right.shape[0] != frame_count:
        raise ValueError(f"Frame-count mismatch in raw extraction: {path}")
    if timestamps.shape != (frame_count,) or indices.shape != (frame_count,):
        raise ValueError(f"Invalid timestamps/frame_indices in {path}")
    for key in RAW_KEYS:
        value = data[key]
        if not isinstance(value, np.ndarray) or value.dtype.kind not in "biuf":
            raise TypeError(f"{key} must be a numeric numpy array in {path}")
        if not np.isfinite(value).all():
            raise ValueError(f"{key} contains NaN or Inf in {path}")


def derive_fps(data: Any) -> float:
    if "fps" in data:
        fps = float(np.asarray(data["fps"]).reshape(()))
        if np.isfinite(fps) and fps > 0:
            return fps
    timestamps = np.asarray(data["timestamps"], dtype=np.float64)
    if len(timestamps) > 1:
        delta_ms = float(np.median(np.diff(timestamps)))
        if np.isfinite(delta_ms) and delta_ms > 0:
            return 1000.0 / delta_ms
    return 30.0


def build_candidate(
    row: dict[str, Any],
    source_root: Path,
    interim_path: Path,
    processed_path: Path,
    arrays: dict[str, np.ndarray],
) -> dict[str, Any]:
    source_path = Path(str(row["file"])).resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    if not source_path.is_relative_to(source_root):
        raise ValueError(f"Source path escapes source root: {source_path}")
    label = completion_to_float(row["completion_label"])
    record = build_provenance_record(
        source_video_path=str(source_path),
        subject_id=str(row["subject_id"]).zfill(2),
        exercise_id=int(float(row["exercise_id"])),
        completion_label=label,
        extraction_status=str(row["status"]),
        extractor_version=str(row["extractor_version"]),
        interim_path=str(interim_path.resolve(strict=True)),
        processed_path=str(processed_path.resolve(strict=True)),
        quality_gate_passed=True,
        compute_hash=True,
    )
    record["dataset"] = str(row.get("dataset", "Upper_Limb_Stroke"))
    source_relative = source_path.relative_to(source_root).as_posix()
    if source_relative != str(row["source_relative_path"]).replace("\\", "/"):
        raise ValueError(f"Quality-log source identity mismatch: {source_path}")
    record["source_record_id"] = source_relative
    record["sample_id"] = processed_path.name
    record["label_source"] = "data/indexes/upper_limb_master.csv:completion_label"
    record["subject_source"] = "data/indexes/upper_limb_master.csv:subject_id"
    record["generation_script"] = "scripts/process_features.py"
    record["feature_shape"] = json.dumps(
        {key: list(value.shape) for key, value in arrays.items() if key in {
            "pose_landmarks", "left_hand_landmarks", "right_hand_landmarks", "kinematics"
        }},
        sort_keys=True,
    )
    record["frame_count"] = int(arrays["pose_landmarks"].shape[0])
    record["provenance_hash"] = canonical_provenance_hash(record)
    if record["data_status"] != STATUS_REAL_CANDIDATE:
        raise ValueError(
            f"Candidate failed closed for {processed_path.name}: "
            f"{record['data_status']} {record.get('exclusion_reasons', '')}"
        )
    if str(row.get("source_sha256", "")) != record["source_video_sha256"]:
        raise ValueError(f"Source hash changed since extraction: {source_path}")
    return record


def process_one(
    row: dict[str, Any],
    source_root: Path,
    interim_dir: Path,
    processed_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    if "mock" in str(row["extractor_version"]).lower() or "synthetic" in str(row["extractor_version"]).lower():
        raise ValueError(f"Mock/synthetic extractor is forbidden: {row['extractor_version']}")
    interim_path = (interim_dir / str(row["output"])).resolve(strict=True)
    if not interim_path.is_relative_to(interim_dir.resolve(strict=True)):
        raise ValueError(f"Interim path escape: {interim_path}")
    if compute_sha256(str(interim_path)) != str(row["output_sha256"]):
        raise ValueError(f"Interim hash mismatch: {interim_path}")
    processed_path = processed_dir / interim_path.name

    arrays: dict[str, np.ndarray]
    if processed_path.exists() and not overwrite:
        with np.load(processed_path, allow_pickle=False) as existing:
            arrays = {key: existing[key] for key in existing.files}
        validate_feature_arrays(arrays, str(processed_path))
        expected_interim_hash = str(row["output_sha256"])
        if str(np.asarray(arrays.get("source_interim_sha256", "")).reshape(())) != expected_interim_hash:
            raise ValueError(f"Existing processed feature has stale source hash: {processed_path}")
        if str(np.asarray(arrays.get("processor_version", "")).reshape(())) != PROCESSOR_VERSION:
            raise ValueError(f"Existing processed feature has incompatible processor version: {processed_path}")
    else:
        with np.load(interim_path, allow_pickle=False) as raw:
            validate_raw(raw, interim_path)
            norm_pose, norm_left, norm_right = normalize_landmarks(
                raw["pose_landmarks"], raw["left_hand_landmarks"], raw["right_hand_landmarks"]
            )
            kinematics = get_kinematic_features(norm_pose, fps=derive_fps(raw))
            arrays = {
                "pose_landmarks": np.asarray(norm_pose, dtype=np.float32),
                "left_hand_landmarks": np.asarray(norm_left, dtype=np.float32),
                "right_hand_landmarks": np.asarray(norm_right, dtype=np.float32),
                "kinematics": np.asarray(kinematics, dtype=np.float32),
                "timestamps": np.asarray(raw["timestamps"], dtype=np.float32),
                "frame_indices": np.asarray(raw["frame_indices"], dtype=np.int32),
                "source_interim_sha256": np.asarray(str(row["output_sha256"])),
                "processor_version": np.asarray(PROCESSOR_VERSION),
            }
            for mask_key in ("pose_mask", "left_hand_mask", "right_hand_mask"):
                if mask_key in raw:
                    arrays[mask_key] = np.asarray(raw[mask_key], dtype=bool)
        validate_feature_arrays(arrays, str(processed_path))
        atomic_save_npz(processed_path, arrays)
    return build_candidate(row, source_root, interim_path, processed_path, arrays)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-log", type=Path, default=DEFAULT_QUALITY_LOG)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--interim-dir", type=Path, default=DEFAULT_INTERIM_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--provenance-candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--errors", type=Path, default=DEFAULT_ERRORS)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.quality_log.is_file():
        raise FileNotFoundError(f"Stage 3 quality log does not exist: {args.quality_log}")
    legacy_interim = (PROJECT_ROOT / "data" / "interim" / "keypoints").resolve()
    legacy_processed = (PROJECT_ROOT / "data" / "processed" / "keypoints").resolve()
    if args.interim_dir.resolve() == legacy_interim or args.processed_dir.resolve() == legacy_processed:
        raise ValueError("Refusing to use legacy mixed mock/real feature directories.")

    quality = pd.read_csv(args.quality_log, dtype={"subject_id": str}).fillna("")
    required = {
        "dataset", "file", "source_relative_path", "source_sha256", "subject_id",
        "exercise_id", "completion_label", "output", "output_sha256", "status",
        "extractor_version",
    }
    missing = sorted(required - set(quality.columns))
    if missing:
        raise ValueError(f"Quality log is missing columns: {missing}")
    if quality["source_relative_path"].astype(str).duplicated().any():
        raise ValueError("Quality log contains duplicate source_relative_path values.")
    successful = quality[quality["status"].astype(str) == "success"]
    if successful.empty:
        raise ValueError("Quality log contains no successful real extractions; no fallback is allowed.")

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    candidates, errors = [], []
    rows = successful.to_dict("records")
    print(f"Processing {len(rows)} quality-approved real extractions.", flush=True)
    for number, row in enumerate(rows, start=1):
        try:
            candidate = process_one(
                row, args.source_root, args.interim_dir, args.processed_dir, args.overwrite
            )
            candidates.append(candidate)
            status = "success"
        except Exception as exc:
            errors.append({
                "source_relative_path": row.get("source_relative_path", ""),
                "output": row.get("output", ""),
                "error": f"{type(exc).__name__}: {exc}",
            })
            status = "error"
        if number % 10 == 0 or number == len(rows):
            if candidates:
                atomic_write_csv(args.provenance_candidates, candidates)
            atomic_write_csv(args.errors, errors)
        print(f"[{number}/{len(rows)}] {status}: {row.get('output', '')}", flush=True)

    statuses = Counter(item["data_status"] for item in candidates)
    print(f"Candidate status counts: {dict(sorted(statuses.items()))}", flush=True)
    print(f"Processing errors: {len(errors)}", flush=True)
    print(f"Candidates: {args.provenance_candidates.resolve()}", flush=True)
    print("Global normalization was not fitted; each LOSO fold must fit train-only statistics.", flush=True)
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
