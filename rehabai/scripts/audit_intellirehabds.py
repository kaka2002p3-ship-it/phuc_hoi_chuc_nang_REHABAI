"""Deep, read-only audit of IntelliRehabDS skeleton files.

The result is an auxiliary-data audit only.  It never maps gestures 0--8 to
the immutable RehabAI Exercise_1--Exercise_4 registry and never writes a train
manifest for the product model.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = (
    Path(__file__).resolve().parents[2]
    / "RehabAI_Datasets_FULL_VERIFIED"
    / "04_Public_Auxiliary_2026"
    / "intellirehabds"
    / "extracted"
    / "SkeletonData"
    / "SkeletonData"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "reports" / "data_provenance"

HEADER = "Version0.1"
JOINT_COUNT = 25
COORDS_PER_JOINT = 3


def parse_name(path: Path) -> dict[str, str]:
    parts = path.stem.split("_")
    # SubjectID_DateID_GestureLabel_RepetitionNumber_CorrectLabel_Position
    if len(parts) < 5:
        return {"subject_id": "", "session_id": "", "gesture": "", "repetition": "", "correct": "", "position": ""}
    return {
        "subject_id": parts[0],
        "session_id": parts[1],
        "gesture": parts[2],
        "repetition": parts[3],
        "correct": parts[4],
        "position": "_".join(parts[5:]),
    }


def parse_frame(line: str) -> tuple[int, list[float], int]:
    # RawData rows are timestamp, camera metadata, then 25 tuples.  Extracting
    # the numeric tuple payload is deliberately strict enough to detect broken
    # rows while ignoring the textual joint names/status values.
    tuples = re.findall(r"\(([^()]*)\)", line)
    if len(tuples) != JOINT_COUNT:
        raise ValueError(f"expected {JOINT_COUNT} joint tuples, got {len(tuples)}")
    values: list[float] = []
    for item in tuples:
        fields = item.split(",")
        if len(fields) != 7:
            raise ValueError(f"joint tuple has {len(fields)} fields instead of 7")
        values.extend(float(value) for value in fields[2:5])
    prefix = line.split(",", 3)
    if len(prefix) < 3:
        raise ValueError("missing frame prefix")
    timestamp = int(prefix[0])
    return timestamp, values, len(tuples)


def audit_file(path: Path) -> dict[str, object]:
    meta = parse_name(path)
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    errors: list[str] = []
    frame_count = 0
    values_seen = 0
    nan_count = 0
    inf_count = 0
    min_value = math.inf
    max_value = -math.inf
    timestamps: list[int] = []
    if not lines or lines[0].strip() != HEADER:
        errors.append("missing Version0.1 header")
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        try:
            timestamp, values, joint_count = parse_frame(line)
            timestamps.append(timestamp)
            frame_count += 1
            values_seen += len(values)
            for value in values:
                if math.isnan(value):
                    nan_count += 1
                elif math.isinf(value):
                    inf_count += 1
                else:
                    min_value = min(min_value, value)
                    max_value = max(max_value, value)
            if joint_count != JOINT_COUNT:
                errors.append(f"line {line_number}: joint_count={joint_count}")
        except Exception as exc:  # noqa: BLE001 - keep all file-level failures
            errors.append(f"line {line_number}: {exc}")

    if meta["correct"] not in {"1", "2"}:
        errors.append(f"unexpected correctness label {meta['correct']!r}")
    if frame_count == 0:
        errors.append("no frames")
    if values_seen != frame_count * JOINT_COUNT * COORDS_PER_JOINT:
        errors.append("coordinate count mismatch")
    if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        errors.append("timestamps are not strictly increasing")
    return {
        **meta,
        "relative_path": path.relative_to(ROOT).as_posix(),
        "frame_count": frame_count,
        "coordinate_count": values_seen,
        "min_xyz": None if min_value is math.inf else min_value,
        "max_xyz": None if max_value is -math.inf else max_value,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "status": "PASS" if not errors else "FAIL",
        "errors": " | ".join(errors),
    }


def main() -> None:
    raw_dir = ROOT / "RawData"
    simplified_dir = ROOT / "Simplified"
    files = sorted(raw_dir.glob("*.txt"))
    if not files:
        raise FileNotFoundError(raw_dir)
    rows = [audit_file(path) for path in files]
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "intellirehabds_sequence_audit.csv"
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    valid = [row for row in rows if row["status"] == "PASS"]
    subject_counts = Counter(row["subject_id"] for row in rows)
    gesture_counts = Counter(row["gesture"] for row in rows)
    correctness_counts = Counter(row["correct"] for row in rows)
    frame_counts = [int(row["frame_count"]) for row in rows]
    summary = {
        "dataset": "IntelliRehabDS",
        "audit_status": "PASS_STRUCTURAL_AND_SEQUENCE_VALUES" if len(valid) == len(rows) else "FAIL_SEQUENCE_VALIDATION",
        "raw_sequence_count": len(rows),
        "simplified_sequence_count": len(list(simplified_dir.glob("*.txt"))),
        "valid_sequence_count": len(valid),
        "invalid_sequence_count": len(rows) - len(valid),
        "subject_count_from_filename": len(subject_counts),
        "subject_counts": dict(sorted(subject_counts.items())),
        "gesture_source_counts": dict(sorted(gesture_counts.items())),
        "correctness_source_counts": dict(sorted(correctness_counts.items())),
        "frame_count": {
            "min": min(frame_counts),
            "max": max(frame_counts),
            "mean": sum(frame_counts) / len(frame_counts),
        },
        "joint_schema": {"joints": JOINT_COUNT, "xyz_coordinates_per_joint": COORDS_PER_JOINT, "coordinate_format": "3D"},
        "product_registry_mapping": "FORBIDDEN",
        "admission_status": "AUXILIARY_ONLY_PENDING_PREDECLARED_SSL_OR_ADAPTER_PROTOCOL",
        "notes": [
            "Gesture labels 0--8 are source ontology and are not Exercise_1--Exercise_4.",
            "CorrectLabel 1/2 is source correctness and is not the Upper Limb completion head.",
            "Filename-derived subject IDs are suitable for this source audit; no product split is created.",
            "The source README reports 15 patients and 14 healthy participants; subject prefixes are retained verbatim.",
        ],
    }
    (OUT / "intellirehabds_sequence_audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = [
        "# IntelliRehabDS deep audit",
        "",
        "This is a read-only auxiliary-data audit. No source gesture is mapped to",
        "the immutable RehabAI product registry and no product training manifest is created.",
        "",
        f"- Status: `{summary['audit_status']}`",
        f"- Sequences: {len(rows)} raw; {summary['simplified_sequence_count']} simplified; valid={len(valid)}",
        f"- Subjects identified from source filenames: {summary['subject_count_from_filename']}",
        f"- Gestures (source ontology): {dict(sorted(gesture_counts.items()))}",
        f"- Correctness labels (source ontology): {dict(sorted(correctness_counts.items()))}",
        f"- Frame count range: {min(frame_counts)}–{max(frame_counts)} (mean {sum(frame_counts)/len(frame_counts):.2f})",
        "- Joint schema: 25 Kinect joints × XYZ (75 values/frame)",
        "",
        "## Recommended next experiment",
        "",
        "Use IntelliRehabDS only for a predeclared self-supervised motion encoder",
        "or source-correctness auxiliary task. Keep all product subjects and labels",
        "isolated, fit normalization within each training partition, and evaluate",
        "the frozen encoder on the existing strict LOSO folds without architecture",
        "selection on their test results.",
    ]
    (OUT / "INTELLIREHABDS_DEEP_AUDIT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
