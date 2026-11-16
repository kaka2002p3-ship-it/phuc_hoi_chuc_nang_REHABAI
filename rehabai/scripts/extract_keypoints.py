"""Extract real MediaPipe keypoints into an isolated, resumable Stage 3 workspace."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = PROJECT_ROOT / "data" / "indexes" / "upper_limb_master.csv"
DEFAULT_SOURCE_ROOT = PROJECT_ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED" / "01_Upper_Limb_Stroke"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "stage3_real" / "interim" / "keypoints"
DEFAULT_QUALITY_LOG = PROJECT_ROOT / "data" / "stage3_real" / "indexes" / "extraction_quality.csv"
EXTRACTOR_VERSION = "MediaPipe Holistic real-v1"
TERMINAL_STATUSES = {"success", "rejected_too_short", "rejected_high_pose_missing"}
LOG_COLUMNS = [
    "dataset", "file", "source_relative_path", "source_sha256", "subject_id",
    "exercise_id", "completion_label", "output", "output_sha256", "status",
    "frames", "pose_missing_rate", "lh_missing_rate", "rh_missing_rate",
    "extractor_version", "error",
]


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        normalized = [{column: record.get(column, "") for column in LOG_COLUMNS} for record in records]
        pd.DataFrame(normalized, columns=LOG_COLUMNS).to_csv(temp_name, index=False)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def interpolate_missing(landmarks: np.ndarray) -> np.ndarray:
    frame_count = landmarks.shape[0]
    if frame_count == 0:
        return landmarks
    is_missing = np.all(landmarks == 0, axis=(1, 2))
    if not np.any(is_missing):
        return landmarks
    table = pd.DataFrame(landmarks.reshape(frame_count, -1))
    table.loc[is_missing, :] = np.nan
    table = table.interpolate(method="linear", limit=5, limit_direction="forward")
    table = table.interpolate(method="linear", limit=5, limit_direction="backward")
    return table.fillna(0).to_numpy(dtype=landmarks.dtype).reshape(landmarks.shape)


def extract_from_video(video_path: str) -> dict[str, np.ndarray] | None:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        return None
    pose_frames, pose_world_frames, left_frames, right_frames = [], [], [], []
    timestamps, frame_indices = [], []
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0:
        fps = 30.0
    try:
        with mp.solutions.holistic.Holistic(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            refine_face_landmarks=False,
        ) as holistic:
            frame_idx = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                result = holistic.process(rgb)
                pose = (
                    np.asarray([[p.x, p.y, p.z, p.visibility] for p in result.pose_landmarks.landmark], dtype=np.float32)
                    if result.pose_landmarks else np.zeros((33, 4), dtype=np.float32)
                )
                pose_world = (
                    np.asarray([[p.x, p.y, p.z, p.visibility] for p in result.pose_world_landmarks.landmark], dtype=np.float32)
                    if result.pose_world_landmarks else np.zeros((33, 4), dtype=np.float32)
                )
                left = (
                    np.asarray([[p.x, p.y, p.z] for p in result.left_hand_landmarks.landmark], dtype=np.float32)
                    if result.left_hand_landmarks else np.zeros((21, 3), dtype=np.float32)
                )
                right = (
                    np.asarray([[p.x, p.y, p.z] for p in result.right_hand_landmarks.landmark], dtype=np.float32)
                    if result.right_hand_landmarks else np.zeros((21, 3), dtype=np.float32)
                )
                pose_frames.append(pose)
                pose_world_frames.append(pose_world)
                left_frames.append(left)
                right_frames.append(right)
                timestamps.append(frame_idx / fps * 1000.0)
                frame_indices.append(frame_idx)
                frame_idx += 1
    finally:
        capture.release()
    if not pose_frames:
        return None
    return {
        "pose_landmarks": np.asarray(pose_frames, dtype=np.float32),
        "pose_world_landmarks": np.asarray(pose_world_frames, dtype=np.float32),
        "left_hand_landmarks": np.asarray(left_frames, dtype=np.float32),
        "right_hand_landmarks": np.asarray(right_frames, dtype=np.float32),
        "timestamps": np.asarray(timestamps, dtype=np.float32),
        "frame_indices": np.asarray(frame_indices, dtype=np.int32),
        "fps": np.asarray(fps, dtype=np.float32),
    }


def process_single_video(task: dict[str, Any]) -> dict[str, Any]:
    base = {
        key: task[key] for key in (
            "dataset", "file", "source_relative_path", "source_sha256",
            "subject_id", "exercise_id", "completion_label", "output",
        )
    }
    base.update({"extractor_version": EXTRACTOR_VERSION, "error": ""})
    try:
        data = extract_from_video(task["file"])
        if data is None:
            return {**base, "status": "error_read", "error": "Video could not be opened or contained no frames."}
        pose = data["pose_landmarks"]
        left = data["left_hand_landmarks"]
        right = data["right_hand_landmarks"]
        pose_mask = ~np.all(pose[:, :, :3] == 0, axis=2)
        left_mask = ~np.all(left == 0, axis=2)
        right_mask = ~np.all(right == 0, axis=2)
        pose_missing = float(np.mean(~pose_mask))
        left_missing = float(np.mean(~left_mask))
        right_missing = float(np.mean(~right_mask))
        data["pose_landmarks"] = interpolate_missing(pose)
        data["pose_world_landmarks"] = interpolate_missing(data["pose_world_landmarks"])
        data["left_hand_landmarks"] = interpolate_missing(left)
        data["right_hand_landmarks"] = interpolate_missing(right)
        data["pose_mask"] = pose_mask
        data["left_hand_mask"] = left_mask
        data["right_hand_mask"] = right_mask
        output_path = Path(task["output_path"])
        atomic_save_npz(output_path, data)
        frame_count = int(len(data["timestamps"]))
        status = "success"
        if frame_count < 30:
            status = "rejected_too_short"
        elif pose_missing > 0.3:
            status = "rejected_high_pose_missing"
        return {
            **base,
            "output_sha256": compute_sha256(output_path),
            "status": status,
            "frames": frame_count,
            "pose_missing_rate": pose_missing,
            "lh_missing_rate": left_missing,
            "rh_missing_rate": right_missing,
        }
    except Exception as exc:
        return {**base, "status": "error_exception", "error": f"{type(exc).__name__}: {exc}"}


def _safe_output_name(row: dict[str, Any], relative_path: str) -> str:
    identity = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:10]
    stem = Path(str(row["file"])).stem
    subject = str(row["subject_id"]).zfill(2)
    exercise = int(float(row["exercise_id"]))
    return f"UL_{subject}_{exercise}_{stem}_{identity}.npz"


def prepare_tasks(
    index_csv: Path,
    source_root: Path,
    output_dir: Path,
    existing: dict[str, dict[str, Any]],
    overwrite: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_resolved = source_root.resolve(strict=True)
    frame = pd.read_csv(index_csv, dtype={"subject_id": str})
    required = {"dataset", "file", "relative_path", "subject_id", "exercise_id", "completion_label"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Index is missing required columns: {missing}")
    if frame["file"].astype(str).duplicated().any() or frame["relative_path"].astype(str).duplicated().any():
        raise ValueError("Index contains duplicate source file or relative_path values.")
    tasks, resumed = [], []
    output_names = set()
    for row in frame.to_dict("records"):
        source = Path(str(row["file"])).resolve(strict=True)
        if not source.is_relative_to(source_resolved):
            raise ValueError(f"Source path escapes source root: {source}")
        relative = source.relative_to(source_resolved).as_posix()
        if (source_resolved / Path(str(row["relative_path"]))).resolve(strict=True) != source:
            raise ValueError(f"Index relative_path does not match file: {row['relative_path']}")
        source_hash = compute_sha256(source)
        output_name = _safe_output_name(row, relative)
        if output_name in output_names:
            raise ValueError(f"Output-name collision: {output_name}")
        output_names.add(output_name)
        output_path = output_dir / output_name
        previous = existing.get(relative)
        if previous and not overwrite:
            resumable = (
                str(previous.get("status")) in TERMINAL_STATUSES
                and output_path.is_file()
                and previous.get("source_sha256") == source_hash
                and previous.get("output_sha256") == compute_sha256(output_path)
            )
            if resumable:
                resumed.append(previous)
                continue
        retrying_logged_error = previous and str(previous.get("status", "")).startswith("error")
        if output_path.exists() and not overwrite and not retrying_logged_error:
            raise ValueError(
                f"Untrusted or stale output exists: {output_path}. "
                "Review it, then rerun with --overwrite if intended."
            )
        tasks.append({
            "dataset": str(row["dataset"]),
            "file": str(source),
            "source_relative_path": relative,
            "source_sha256": source_hash,
            "subject_id": str(row["subject_id"]).zfill(2),
            "exercise_id": int(float(row["exercise_id"])),
            "completion_label": str(row["completion_label"]).strip().lower(),
            "output": output_name,
            "output_path": str(output_path),
        })
    return tasks, resumed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-csv", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--quality-log", type=Path, default=DEFAULT_QUALITY_LOG)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 8:
        raise ValueError("--workers must be between 1 and 8.")
    legacy_output = (PROJECT_ROOT / "data" / "interim" / "keypoints").resolve()
    legacy_log = (PROJECT_ROOT / "data" / "indexes" / "extraction_quality.csv").resolve()
    if args.output_dir.resolve() == legacy_output or args.quality_log.resolve() == legacy_log:
        raise ValueError("Refusing to write Stage 3 results into legacy mixed mock/real locations.")
    existing_records = []
    if args.quality_log.exists():
        existing_records = pd.read_csv(
            args.quality_log, dtype={"subject_id": str}
        ).fillna("").to_dict("records")
    identities = [str(item.get("source_relative_path", "")) for item in existing_records]
    if len(identities) != len(set(identities)):
        raise ValueError("Quality log contains duplicate source_relative_path values.")
    existing = {str(item["source_relative_path"]): item for item in existing_records}
    tasks, resumed = prepare_tasks(
        args.index_csv, args.source_root, args.output_dir, existing, args.overwrite
    )
    records_by_source = {str(item["source_relative_path"]): item for item in resumed}
    print(
        f"Stage 3 extraction: total={len(tasks) + len(resumed)}, "
        f"resume={len(resumed)}, pending={len(tasks)}",
        flush=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    error_count = 0
    if tasks:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_single_video, task): task for task in tasks}
            for number, future in enumerate(as_completed(futures), start=1):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        **task,
                        "status": "error_worker",
                        "error": f"{type(exc).__name__}: {exc}",
                        "extractor_version": EXTRACTOR_VERSION,
                    }
                result.pop("output_path", None)
                records_by_source[str(result["source_relative_path"])] = result
                if str(result["status"]).startswith("error"):
                    error_count += 1
                atomic_write_csv(
                    args.quality_log,
                    sorted(records_by_source.values(), key=lambda item: str(item["source_relative_path"])),
                )
                print(f"[{number}/{len(tasks)}] {result['status']}: {result['output']}", flush=True)
    elif resumed:
        atomic_write_csv(
            args.quality_log,
            sorted(records_by_source.values(), key=lambda item: str(item["source_relative_path"])),
        )
    statuses = Counter(str(item.get("status", "unknown")) for item in records_by_source.values())
    print(f"Extraction status counts: {dict(sorted(statuses.items()))}", flush=True)
    print(f"Quality log: {args.quality_log.resolve()}", flush=True)
    return 2 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
