"""Resumable, sparse MediaPipe extraction for MobiPhysio pretraining videos."""
from __future__ import annotations

import argparse
import atexit
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "external_pretraining_v1" / "mobiphysio_manifest.csv"
_HOLISTIC = None


def initialize_worker() -> None:
    """Load MediaPipe once per process instead of once per video."""
    global _HOLISTIC
    _HOLISTIC = mp.solutions.holistic.Holistic(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        refine_face_landmarks=False,
    )
    atexit.register(_HOLISTIC.close)


def _holistic():
    global _HOLISTIC
    if _HOLISTIC is None:
        initialize_worker()
    return _HOLISTIC


def _landmarks(result):
    pose = (
        np.asarray([[x.x, x.y, x.z] for x in result.pose_landmarks.landmark], np.float32)
        if result and result.pose_landmarks else np.zeros((33, 3), np.float32)
    )
    left = (
        np.asarray([[x.x, x.y, x.z] for x in result.left_hand_landmarks.landmark], np.float32)
        if result and result.left_hand_landmarks else np.zeros((21, 3), np.float32)
    )
    right = (
        np.asarray([[x.x, x.y, x.z] for x in result.right_hand_landmarks.landmark], np.float32)
        if result and result.right_hand_landmarks else np.zeros((21, 3), np.float32)
    )
    return pose, left, right


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".csv", dir=path.parent)
    os.close(fd)
    try:
        frame.to_csv(temp, index=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def inspect_feature(path: Path, target_frames: int) -> tuple[str, float] | None:
    """Validate an existing artifact and recover its real pose-missing rate."""
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            pose = np.asarray(data["pose_landmarks"], dtype=np.float32)
            left = np.asarray(data["left_hand_landmarks"], dtype=np.float32)
            right = np.asarray(data["right_hand_landmarks"], dtype=np.float32)
        if pose.shape != (target_frames, 33, 3):
            return None
        if left.shape != (target_frames, 21, 3) or right.shape != (target_frames, 21, 3):
            return None
        if not (np.isfinite(pose).all() and np.isfinite(left).all() and np.isfinite(right).all()):
            return None
        missing = float(np.mean(~np.any(pose, axis=(1, 2))))
        return ("ready", missing) if missing <= 0.30 else ("rejected_high_pose_missing", missing)
    except (KeyError, OSError, ValueError):
        return None


def extract(row: dict, target_frames: int) -> tuple[str, str, float]:
    source, output = Path(row["source_path"]), Path(row["feature_path"])
    existing = inspect_feature(output, target_frames)
    if existing is not None:
        return row["sample_id"], existing[0], existing[1]
    cap = cv2.VideoCapture(str(source))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not cap.isOpened() or count < 30:
        cap.release()
        return row["sample_id"], "rejected_too_short", 1.0
    # Sequential grabs avoid expensive random seeks to 96 positions in a
    # compressed video. Duplicate indices are kept for videos shorter than the
    # target sequence, preserving the exact fixed-length contract.
    indices = np.linspace(0, count - 1, target_frames).round().astype(int)
    selected = set(int(index) for index in indices)
    decoded = {}
    try:
        for frame_index in range(count):
            ok = cap.grab()
            if not ok:
                break
            if frame_index not in selected:
                continue
            retrieved, frame = cap.retrieve()
            result = (
                _holistic().process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if retrieved else None
            )
            decoded[frame_index] = _landmarks(result)
    finally:
        cap.release()
    missing_pose = np.zeros((33, 3), np.float32)
    missing_hand = np.zeros((21, 3), np.float32)
    fallback = (missing_pose, missing_hand, missing_hand)
    samples = [decoded.get(int(index), fallback) for index in indices]
    pose = np.asarray([sample[0] for sample in samples], dtype=np.float32)
    left = np.asarray([sample[1] for sample in samples], dtype=np.float32)
    right = np.asarray([sample[2] for sample in samples], dtype=np.float32)
    missing = int(np.count_nonzero(~np.any(pose, axis=(1, 2))))
    rate = missing / target_frames
    status = "ready" if rate <= 0.30 else "rejected_high_pose_missing"
    if status == "ready":
        atomic_npz(output, pose_landmarks=pose, left_hand_landmarks=left, right_hand_landmarks=right)
    return row["sample_id"], status, rate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--target-frames", type=int, default=96)
    parser.add_argument("--limit", type=int, default=0, help="Pilot-only row limit; zero means all pending rows")
    parser.add_argument("--sync-only", action="store_true")
    args = parser.parse_args()
    frame = pd.read_csv(args.manifest, dtype={"subject_id": str}).fillna("")
    rows = frame.to_dict("records")
    existing = {
        row["sample_id"]: status
        for row in rows
        if (status := inspect_feature(Path(row["feature_path"]), args.target_frames)) is not None
    }
    pending = [] if args.sync_only else [x for x in rows if x["sample_id"] not in existing]
    if args.limit:
        # Deterministic balanced pilot across source exercises.
        pending = pd.DataFrame(pending).groupby("source_exercise_id", group_keys=False).head(max(1, args.limit // 6)).head(args.limit).to_dict("records")
    print(f"MobiPhysio extraction: total={len(rows)} pending={len(pending)} workers={args.workers}", flush=True)
    status_by_id = dict(existing)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize_worker) as pool:
        futures = {pool.submit(extract, row, args.target_frames): row for row in pending}
        for i, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                sample, status, missing = future.result()
                detail = ""
            except Exception as exc:
                sample, status, missing = row["sample_id"], "failed", 1.0
                detail = f" ({type(exc).__name__}: {exc})"
            status_by_id[sample] = (status, missing)
            print(f"[{i}/{len(futures)}] {status}: {sample}{detail}", flush=True)
    for i, row in frame.iterrows():
        if row["sample_id"] in status_by_id:
            frame.at[i, "feature_status"] = status_by_id[row["sample_id"]][0]
            frame.at[i, "pose_missing_rate"] = status_by_id[row["sample_id"]][1]
    atomic_csv(frame, args.manifest)
    # Keep the combined training manifest synchronized with resumable status.
    rehab24 = args.manifest.with_name("rehab24_manifest.csv")
    combined = args.manifest.with_name("external_manifest.csv")
    if rehab24.is_file():
        atomic_csv(pd.concat([pd.read_csv(rehab24), frame], ignore_index=True, sort=False), combined)


if __name__ == "__main__":
    main()
