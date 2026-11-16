"""Create a provenance-neutral index for the extracted ``datanew`` AVI corpus.

The index is intentionally unlabeled: it is suitable for representation
learning/quality auditing, not for supervised product training.  Raw archives
and extracted videos are never modified.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    root = args.source_root.resolve(strict=True)
    videos = sorted(root.rglob("*.avi"))
    if not videos:
        raise SystemExit(f"No AVI files under {root}")
    rows = []
    for i, path in enumerate(videos, 1):
        rows.append({
            "dataset": "datanew_unlabeled",
            "file": str(path.resolve()),
            "relative_path": path.relative_to(root).as_posix(),
            # The archive has recording-group identifiers, not verified human
            # subjects. Keep that distinction explicit; do not infer a person
            # ID from the filename prefix.
            "subject_id": "unknown",
            "exercise_id": 0,
            "completion_label": "unknown",
            "sample_id": f"DATANEW_{i:04d}",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f"index={args.output.resolve()}")
    print(f"videos={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
