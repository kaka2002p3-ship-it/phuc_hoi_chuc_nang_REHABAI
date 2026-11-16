"""Prepare a balanced local exercise index without modifying raw videos.

Expected raw layout (relative to the repository root)::

    data/ex1/<exercise>/*.mp4
    data/ex2/<exercise>/*.mp4

The output is an index compatible with ``extract_keypoints.py``.  Videos are
never copied, renamed, cut, or deleted; only a deterministic subset is put in
the index so classes and subjects have comparable weight.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT.parent / "data"
DEFAULT_OUT = ROOT / "data" / "local_2class" / "local_index.csv"


def stable_key(path: Path) -> str:
    return hashlib.sha256(path.as_posix().encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--per-class", type=int, default=6,
                    help="Maximum videos per subject and class (default: 6)")
    args = ap.parse_args()
    raw = args.raw_root.resolve(strict=True)
    if args.per_class < 1:
        raise ValueError("--per-class must be positive")

    # Exercise 1 is reserved for the future shoulder class.  For this phase
    # the two labels are deliberately local and contiguous: elbow=1, hand=2.
    label_rules = {
        "khuyu tay": 1,
        "gập khuỷu tay": 1,
        "gap khuyu tay": 1,
        "mo ban tay": 2,
        "mở bàn tay": 2,
        "mo ban tay ": 2,
    }
    rows = []
    summary = {}
    subject_dirs = sorted(
        p for p in raw.iterdir()
        if p.is_dir() and (
            (p.name.lower().startswith("ex") and p.name[2:].isdigit())
            or (p.name.lower().startswith("p") and p.name[1:].isdigit())
        )
    )
    for subject_dir in subject_dirs:
        digits = "".join(character for character in subject_dir.name if character.isdigit())
        subject = digits.zfill(2)
        grouped: dict[int, list[Path]] = {1: [], 2: []}
        for exercise_dir in sorted(p for p in subject_dir.iterdir() if p.is_dir()):
            key = " ".join(exercise_dir.name.strip().lower().split())
            exercise_id = label_rules.get(key)
            if exercise_id is None:
                raise ValueError(f"Unrecognized exercise folder: {exercise_dir}")
            grouped[exercise_id].extend(sorted(exercise_dir.glob("*.mp4"), key=stable_key))
        summary[subject] = {}
        for exercise_id, files in grouped.items():
            selected = files[: args.per_class]
            summary[subject][str(exercise_id)] = {
                "available": len(files), "selected": len(selected)
            }
            if not selected:
                raise ValueError(f"Subject {subject} has no files for exercise {exercise_id}")
            for path in selected:
                rows.append({
                    "dataset": "LocalRehab2Class",
                    "file": str(path.resolve()),
                    "relative_path": path.resolve().relative_to(raw).as_posix(),
                    "subject_id": subject,
                    "exercise_id": exercise_id,
                    # The strict provenance schema stores completion as 0/1.
                    "completion_label": 1.0,
                })

    if len({r["subject_id"] for r in rows}) < 2:
        raise ValueError("At least two subject directories (for example ex1, ex2) are required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["subject_id"], r["exercise_id"], r["relative_path"])))
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps({"per_class": args.per_class, "subjects": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"index={args.output.resolve()}")
    print(f"summary={summary_path.resolve()}")
    print(f"selected_videos={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
