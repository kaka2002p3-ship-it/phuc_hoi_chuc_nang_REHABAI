"""Sparse, reproducible MediaPipe extraction for the unlabeled datanew AVI set."""
from __future__ import annotations

import argparse
import atexit
import hashlib
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd

from shared.preprocessing.kinematics import get_kinematic_features
from shared.preprocessing.normalization import normalize_landmarks

_HOLISTIC = None


def initialize_worker() -> None:
    global _HOLISTIC
    _HOLISTIC = mp.solutions.holistic.Holistic(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        refine_face_landmarks=False,
    )
    atexit.register(_HOLISTIC.close)


def holistic():
    global _HOLISTIC
    if _HOLISTIC is None:
        initialize_worker()
    return _HOLISTIC


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def landmarks(result):
    pose = np.asarray([[p.x, p.y, p.z] for p in result.pose_landmarks.landmark], np.float32) if result and result.pose_landmarks else np.zeros((33, 3), np.float32)
    left = np.asarray([[p.x, p.y, p.z] for p in result.left_hand_landmarks.landmark], np.float32) if result and result.left_hand_landmarks else np.zeros((21, 3), np.float32)
    right = np.asarray([[p.x, p.y, p.z] for p in result.right_hand_landmarks.landmark], np.float32) if result and result.right_hand_landmarks else np.zeros((21, 3), np.float32)
    return pose, left, right


def extract_one(task: dict) -> dict:
    source = Path(task["file"]); output = Path(task["output"])
    try:
        cap = cv2.VideoCapture(str(source))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not cap.isOpened() or count < 30:
            cap.release(); return {**task, "status": "rejected_too_short", "frames": count, "pose_missing_rate": 1.0, "error": "cannot open or fewer than 30 frames"}
        if not np.isfinite(fps) or fps <= 0: fps = 30.0
        indices = np.linspace(0, count - 1, int(task["target_frames"])).round().astype(int)
        selected = set(int(i) for i in indices); decoded = {}
        for i in range(count):
            if not cap.grab(): break
            if i not in selected: continue
            ok, frame = cap.retrieve()
            result = holistic().process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) if ok else None
            decoded[i] = landmarks(result)
        cap.release()
        fallback = (np.zeros((33, 3), np.float32), np.zeros((21, 3), np.float32), np.zeros((21, 3), np.float32))
        samples = [decoded.get(int(i), fallback) for i in indices]
        pose = np.asarray([x[0] for x in samples], np.float32)
        left = np.asarray([x[1] for x in samples], np.float32)
        right = np.asarray([x[2] for x in samples], np.float32)
        pose_mask = np.any(pose, axis=2); left_mask = np.any(left, axis=2); right_mask = np.any(right, axis=2)
        pose_missing = float(np.mean(~pose_mask))
        # Normalize only visible landmarks; zero landmarks must remain zero.
        norm_pose, norm_left, norm_right = normalize_landmarks(pose, left, right)
        norm_pose[~pose_mask] = 0.0; norm_left[~left_mask] = 0.0; norm_right[~right_mask] = 0.0
        kin = get_kinematic_features(norm_pose, fps=30.0)
        status = "ready" if pose_missing <= 0.30 else "rejected_high_pose_missing"
        if status == "ready":
            atomic_npz(output, pose_landmarks=norm_pose, left_hand_landmarks=norm_left, right_hand_landmarks=norm_right,
                       kinematics=kin.astype(np.float32), pose_mask=pose_mask, left_hand_mask=left_mask,
                       right_hand_mask=right_mask, frame_indices=indices.astype(np.int32),
                       timestamps=(indices / fps * 1000.0).astype(np.float32), fps=np.asarray(fps, np.float32))
            out_hash = sha256(output)
        else:
            out_hash = ""
        return {**task, "status": status, "frames": int(count), "sampled_frames": len(indices), "fps": fps,
                "pose_missing_rate": pose_missing, "output_sha256": out_hash, "error": ""}
    except Exception as exc:
        return {**task, "status": "error", "frames": 0, "sampled_frames": 0, "fps": 0,
                "pose_missing_rate": 1.0, "output_sha256": "", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--target-frames", type=int, default=96)
    ap.add_argument("--sample-prefix", default="DATANEW")
    args = ap.parse_args()
    root = args.source_root.resolve(strict=True); args.output_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".avi", ".mp4", ".mov"})
    tasks = [{"sample_id": f"{args.sample_prefix}_{i:04d}", "file": str(p.resolve()),
              "relative_path": p.relative_to(root).as_posix(),
              "output": str((args.output_dir / f"{args.sample_prefix}_{i:04d}.npz").resolve()),
              "target_frames": args.target_frames} for i, p in enumerate(videos, 1)]
    existing = {}
    if args.manifest.is_file():
        existing = {str(r.get("sample_id")): r for r in pd.read_csv(args.manifest).fillna("").to_dict("records")}
    pending = [t for t in tasks if not (Path(t["output"]).is_file() and existing.get(t["sample_id"], {}).get("status") == "ready")]
    results = {k: v for k, v in existing.items() if k in {t["sample_id"] for t in tasks}}
    print(f"datanew extraction total={len(tasks)} pending={len(pending)} workers={args.workers}", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize_worker) as pool:
        futures = {pool.submit(extract_one, t): t for t in pending}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result(); results[result["sample_id"]] = result
            pd.DataFrame(sorted(results.values(), key=lambda x: x["sample_id"])).to_csv(args.manifest, index=False)
            print(f"[{i}/{len(pending)}] {result['status']} {result['sample_id']} missing={result.get('pose_missing_rate', 1):.3f}", flush=True)
    frame = pd.DataFrame(sorted(results.values(), key=lambda x: x["sample_id"]))
    frame.to_csv(args.manifest, index=False)
    print(frame["status"].value_counts().to_dict())
    return 0 if not frame["status"].astype(str).str.startswith("error").any() else 2


if __name__ == "__main__":
    raise SystemExit(main())
