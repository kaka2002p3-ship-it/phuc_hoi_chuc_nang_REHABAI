"""Prepare leakage-safe external pretraining manifests/features for datasets 02/03.

REHAB24-6 is converted from its released 30-fps 2D joint tracks and segmented
at repetition boundaries. MobiPhysio remains video-backed and is extracted by
``extract_external_keypoints.py``. Source exercise IDs are deliberately kept
in a dataset-specific namespace and never mapped to product classes 1..4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED"
WORK = ROOT / "data" / "external_pretraining_v1"
R24 = DATASETS / "02_REHAB24-6"
MOBI = DATASETS / "03_MobiPhysio" / "dataset"
MOBI_EXERCISES = {
    1: "Abduction", 2: "Adduction", 3: "Lateral Rotation",
    4: "Medial Rotation", 5: "Circumduction", 6: "Wrist Extension",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def convert_rehab24(output: Path) -> list[dict]:
    seg = pd.read_csv(R24 / "Segmentation.csv", sep=";")
    out_dir = output / "features" / "rehab24"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    # Dataset joints: shoulder 6/11, elbow 7/12, wrist/hand 8/13.
    mp_map = {11: 6, 13: 7, 15: 8, 12: 11, 14: 12, 16: 13}
    for row in seg.itertuples(index=False):
        source = R24 / "2d_joints" / f"Ex{int(row.exercise_id)}" / f"{row.video_id}-c17-30fps.npy"
        if not source.is_file():
            continue
        tracks = np.load(source, mmap_mode="r")
        # The released segmentation boundaries index the 30-fps arrays (the
        # 120-fps arrays are exactly 4x longer); no /4 conversion is needed.
        first = max(0, int(row.first_frame))
        last = min(len(tracks), int(row.last_frame) + 1)
        if last - first < 30:
            continue
        x = np.asarray(tracks[first:last], dtype=np.float32)
        pose = np.zeros((len(x), 33, 3), dtype=np.float32)
        for mp_idx, src_idx in mp_map.items():
            pose[:, mp_idx, :2] = x[:, src_idx, :2]
        center = (pose[:, 11, :2] + pose[:, 12, :2]) / 2.0
        scale = np.linalg.norm(pose[:, 11, :2] - pose[:, 12, :2], axis=1)
        scale[scale < 1e-5] = 1.0
        # Normalize only released joints. Missing MediaPipe landmarks must stay
        # exactly zero rather than becoming translated synthetic coordinates.
        mapped_indices = np.asarray(sorted(mp_map), dtype=np.int64)
        pose[:, mapped_indices, :2] = (
            pose[:, mapped_indices, :2] - center[:, None, :]
        ) / scale[:, None, None]
        name = f"R24_P{int(row.person_id):02d}_E{int(row.exercise_id):02d}_{row.video_id}_R{int(row.repetition_number):03d}.npz"
        np.savez_compressed(out_dir / name, pose_landmarks=pose)
        rows.append({
            "sample_id": name, "dataset": "REHAB24-6", "subject_id": f"R24_{int(row.person_id):02d}",
            "source_exercise_id": int(row.exercise_id), "source_exercise_name": f"REHAB24_Exercise_{int(row.exercise_id)}",
            "correctness": int(row.correctness), "quality_score": "", "feature_path": str((out_dir / name).resolve()),
            "source_path": str(source.resolve()), "source_sha256": sha256(source), "feature_status": "ready",
        })
    return rows


def mobiphysio_manifest(output: Path) -> list[dict]:
    score_path = MOBI / "Physiotherapist Exercise Marking .csv"
    raw = pd.read_csv(score_path)
    scores = raw[raw["Video Name"].notna()].copy()
    scores["quality_score"] = pd.to_numeric(scores["Unnamed: 12"], errors="coerce")
    by_name = dict(zip(scores["Video Name"].astype(str), scores["quality_score"]))
    rows = []
    for source in sorted(MOBI.glob("*.mp4")):
        match = re.match(r"E(\d+)_P(\d+)_", source.stem)
        if not match or int(match.group(1)) not in MOBI_EXERCISES:
            continue
        ex, person = map(int, match.groups())
        rows.append({
            "sample_id": f"MOBI_{source.stem}.npz", "dataset": "MobiPhysio", "subject_id": f"MOBI_{person:02d}",
            "source_exercise_id": ex, "source_exercise_name": MOBI_EXERCISES[ex], "correctness": "",
            "quality_score": float(by_name[source.stem]) if source.stem in by_name and pd.notna(by_name[source.stem]) else "",
            "feature_path": str((output / "features" / "mobiphysio" / f"MOBI_{source.stem}.npz").resolve()),
            "source_path": str(source.resolve()), "source_sha256": sha256(source), "feature_status": "pending",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=WORK)
    parser.add_argument("--skip-rehab24", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    r24 = [] if args.skip_rehab24 else convert_rehab24(args.output)
    mobi = mobiphysio_manifest(args.output)
    columns = ["sample_id", "dataset", "subject_id", "source_exercise_id", "source_exercise_name", "correctness", "quality_score", "feature_path", "source_path", "source_sha256", "feature_status"]
    pd.DataFrame(r24, columns=columns).to_csv(args.output / "rehab24_manifest.csv", index=False)
    pd.DataFrame(mobi, columns=columns).to_csv(args.output / "mobiphysio_manifest.csv", index=False)
    combined = pd.DataFrame(r24 + mobi, columns=columns)
    combined.to_csv(args.output / "external_manifest.csv", index=False)
    policy = {
        "version": "external-pretraining-v1", "target_schema": [96, 237],
        "ontology_policy": "dataset-specific source labels; no mapping to product classes",
        "rehab24": {"samples": len(r24), "subjects": len({x["subject_id"] for x in r24}), "correctness_label": True},
        "mobiphysio": {"samples": len(mobi), "subjects": len({x["subject_id"] for x in mobi}), "exercises": MOBI_EXERCISES, "expert_score_available": sum(x["quality_score"] != "" for x in mobi)},
        "target_evaluation": "data 01 strict LOSO only; external data never enters validation/test",
    }
    (args.output / "dataset_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    print(json.dumps(policy, indent=2))


if __name__ == "__main__":
    main()
