"""Convert admitted IntelliRehabDS skeletons to the shared 96x237 SSL input.

Only the common upper-limb pose/kinematic view is populated. Source gesture and
correctness labels are preserved in the manifest but are not used by SSL.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from shared.preprocessing.kinematics import get_kinematic_features
from shared.preprocessing.sequence import resample_sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "experiments/public_auxiliary_pilot/intellirehabds_pilot_manifest.csv"
DEFAULT_OUTPUT = ROOT / "data/public_auxiliary_pilot/intellirehabds/features"

# Kinect v2 -> MediaPipe indices available in both domains. Hands deliberately
# remain empty: Kinect hand/tip/thumb are not equivalent to MediaPipe's 21 hand
# joints and synthesizing them would create a false cross-domain contract.
KINECT_TO_MEDIAPIPE = {
    4: 11, 5: 13, 6: 15,  # left shoulder, elbow, wrist
    8: 12, 9: 14, 10: 16,  # right shoulder, elbow, wrist
    12: 23, 16: 24,  # left/right hip for trunk kinematics
}
MAX_MISSING_COMMON_JOINT_FRACTION = 0.05
MAX_MISSING_COMMON_JOINT_GAP = 5


def _longest_true_run(mask: np.ndarray) -> int:
    longest = current = 0
    for value in mask:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def repair_common_joints(joints: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Interpolate short Kinect tracking gaps in only the shared joints.

    Zero-valued complete joints are Kinect missing detections.  Long or common
    gaps are rejected instead of fabricating an unreliable motion sequence.
    """
    repaired = joints.copy()
    repaired_frames = np.zeros(len(joints), dtype=bool)
    repaired_values = 0
    for joint in KINECT_TO_MEDIAPIPE:
        missing = np.all(repaired[:, joint] == 0, axis=1)
        count = int(missing.sum())
        if count == 0:
            continue
        if (
            count / len(repaired) > MAX_MISSING_COMMON_JOINT_FRACTION
            or _longest_true_run(missing) > MAX_MISSING_COMMON_JOINT_GAP
            or int((~missing).sum()) < 2
        ):
            raise ValueError(
                f"Unsafe missing-data gap for Kinect joint {joint}: "
                f"missing={count}/{len(repaired)}, longest={_longest_true_run(missing)}"
            )
        timeline = np.arange(len(repaired))
        for coordinate in range(3):
            repaired[missing, joint, coordinate] = np.interp(
                timeline[missing], timeline[~missing], repaired[~missing, joint, coordinate]
            )
        repaired_frames |= missing
        repaired_values += count
    return repaired, int(repaired_frames.sum()), repaired_values


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with np.load(path, allow_pickle=False) as payload:
            x = np.asarray(payload["features"])
        return (
            x.shape == (96, 237)
            and x.dtype == np.float32
            and np.isfinite(x).all()
            and np.count_nonzero(x[:, 99:225]) == 0
        )
    except (KeyError, OSError, ValueError):
        return False


def convert(source: Path, return_repair_counts: bool = False):
    simplified = Path(str(source).replace(f"{os.sep}RawData{os.sep}", f"{os.sep}Simplified{os.sep}"))
    if not simplified.is_file():
        raise FileNotFoundError(f"Matching simplified skeleton is missing: {simplified}")
    skeleton = np.loadtxt(simplified, delimiter=",", dtype=np.float32)
    if skeleton.ndim == 1:
        skeleton = skeleton[None, :]
    if skeleton.ndim != 2 or skeleton.shape[1] != 75 or not np.isfinite(skeleton).all():
        raise ValueError(f"Invalid simplified skeleton {simplified}: {skeleton.shape}")
    joints, repaired_frames, repaired_values = repair_common_joints(skeleton.reshape(-1, 25, 3))
    pose = np.zeros((len(joints), 33, 3), dtype=np.float32)
    left_shoulder, right_shoulder = joints[:, 4], joints[:, 8]
    center = (left_shoulder + right_shoulder) / 2.0
    scale = np.linalg.norm(left_shoulder - right_shoulder, axis=1)
    if np.any(scale < 1e-5):
        raise ValueError(f"Degenerate shoulder width remains after safe interpolation in {simplified}")
    for source_index, target_index in KINECT_TO_MEDIAPIPE.items():
        pose[:, target_index] = (joints[:, source_index] - center) / scale[:, None]
    kinematics = get_kinematic_features(pose, fps=30.0).astype(np.float32)
    # Per-sequence standardization is part of the source/target common-view
    # contract and is repeated inside OptimizedSSLAdapter for target samples.
    kinematics = (kinematics - kinematics.mean(0, keepdims=True)) / np.maximum(
        kinematics.std(0, keepdims=True), 1e-5
    )
    pose = resample_sequence(pose, 96).astype(np.float32)
    kinematics = resample_sequence(kinematics, 96).astype(np.float32)
    hands = np.zeros((96, 126), dtype=np.float32)
    features = np.concatenate([pose.reshape(96, 99), hands, kinematics], axis=1)
    if features.shape != (96, 237) or not np.isfinite(features).all():
        raise ValueError(f"Converted feature contract failed for {source}")
    features = features.astype(np.float32)
    if return_repair_counts:
        return features, repaired_frames, repaired_values
    return features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    frame = pd.read_csv(args.manifest, dtype={"subject_id": str}).fillna("")
    required = {"sample_id", "source_path", "subject_id", "source_fold", "product_split"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Pilot manifest missing columns: {sorted(required - set(frame.columns))}")
    if frame.empty or frame["product_split"].astype(str).ne("NOT_ADMITTED").any():
        raise ValueError("Pilot manifest must be non-empty and product-isolated")
    rows = frame.head(args.limit) if args.limit else frame
    args.output.mkdir(parents=True, exist_ok=True)
    for progress, (index, row) in enumerate(rows.iterrows(), 1):
        target = args.output / f"{row['sample_id']}.npz"
        if not inspect(target):
            features, repaired_frames, repaired_values = convert(
                Path(row["source_path"]), return_repair_counts=True
            )
            atomic_npz(target, features=features)
        else:
            # Recompute source repair metadata so resumed manifests retain the
            # same auditable provenance as a clean run.
            _, repaired_frames, repaired_values = convert(
                Path(row["source_path"]), return_repair_counts=True
            )
        frame.at[index, "ssl_feature_path"] = str(target.resolve())
        frame.at[index, "ssl_feature_status"] = "ready"
        frame.at[index, "ssl_repaired_common_joint_frames"] = repaired_frames
        frame.at[index, "ssl_repaired_common_joint_values"] = repaired_values
        if progress % 100 == 0 or progress == len(rows):
            print(f"prepared={progress}/{len(rows)}", flush=True)
    if not args.limit:
        frame["source_manifest_sha256"] = sha256(args.manifest)
        output_manifest = args.output.parent / "ssl_manifest.csv"
        frame.to_csv(output_manifest, index=False)
        print(f"manifest={output_manifest}")


if __name__ == "__main__":
    main()
