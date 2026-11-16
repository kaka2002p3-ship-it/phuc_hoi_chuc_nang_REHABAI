"""Validate prospective videos before any extraction or model training."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import cv2
import pandas as pd


REQUIRED = {
    "subject_id", "exercise_id", "completion_label", "repetition",
    "planned_filename", "consent_confirmed", "protocol_version", "recording_status",
}
NAME = re.compile(r"^(P\d{3})_E([1-4])_C([01])_R(\d{2})\.mp4$", re.IGNORECASE)


def truthy(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_video(path: Path) -> dict:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return {"readable": False}
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frames / fps if fps > 0 else 0.0
        return {
            "readable": frames > 0 and fps > 0,
            "frames": frames, "fps": fps, "width": width, "height": height,
            "duration_seconds": duration,
        }
    finally:
        capture.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_csv(args.manifest, dtype={"subject_id": str}).fillna("")
    if missing := REQUIRED - set(frame.columns):
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    if frame.empty or frame["planned_filename"].duplicated().any():
        raise ValueError("Manifest must be non-empty with unique filenames")
    records = []
    for row in frame.to_dict("records"):
        reasons = []
        filename = str(row["planned_filename"])
        match = NAME.fullmatch(filename)
        if not match:
            reasons.append("INVALID_PSEUDONYMOUS_FILENAME")
        else:
            encoded = (match.group(1).upper(), int(match.group(2)), int(match.group(3)), int(match.group(4)))
            declared = (str(row["subject_id"]).upper(), int(row["exercise_id"]), int(row["completion_label"]), int(row["repetition"]))
            if encoded != declared:
                reasons.append("FILENAME_LABEL_MISMATCH")
        if not truthy(row["consent_confirmed"]):
            reasons.append("CONSENT_NOT_CONFIRMED")
        if str(row["protocol_version"]) != "prospective-v1":
            reasons.append("PROTOCOL_VERSION_MISMATCH")
        path = args.video_root / filename
        details = inspect_video(path) if path.is_file() else {"readable": False}
        if not path.is_file():
            reasons.append("VIDEO_MISSING")
        elif not details.get("readable"):
            reasons.append("VIDEO_UNREADABLE")
        else:
            if details["fps"] < 20:
                reasons.append("FPS_BELOW_20")
            if min(details["width"], details["height"]) < 720:
                reasons.append("RESOLUTION_BELOW_720P")
            if not 2.0 <= details["duration_seconds"] <= 30.0:
                reasons.append("DURATION_OUTSIDE_2_TO_30_SECONDS")
        records.append({**row, **details, "video_path": str(path.resolve()),
                        "video_sha256": sha256(path) if path.is_file() else "",
                        "quality_gate_passed": not reasons,
                        "exclusion_reasons": "|".join(reasons)})
    result = pd.DataFrame(records)
    ready = result[result.quality_gate_passed]
    subjects = sorted(set(ready.subject_id))
    cell_counts = ready.groupby(["subject_id", "exercise_id", "completion_label"]).size()
    balanced = len(subjects) >= 10 and all(
        cell_counts.get((subject, exercise, completion), 0) >= 5
        for subject in subjects for exercise in range(1, 5) for completion in (0, 1)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    summary = {
        "protocol": "prospective-v1",
        "planned": len(result), "passed": len(ready), "failed": len(result) - len(ready),
        "passed_subjects": len(subjects), "balanced_gate_passed": balanced,
        "eligible_for_extraction": bool(balanced), "eligible_for_training": False,
        "note": "Extraction/provenance verification and a frozen prospective evaluation split are still required.",
    }
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not balanced:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
