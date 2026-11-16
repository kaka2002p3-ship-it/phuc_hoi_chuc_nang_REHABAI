"""Promote explicitly reviewed conversation IDs into approved SFT JSONL."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_ai"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-file", required=True, help="JSON containing reviewer identity and approved sample IDs")
    args = parser.parse_args()
    review_path = Path(args.review_file).resolve()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    reviewer = str(review.get("reviewer_name", "")).strip(); role = str(review.get("reviewer_role", "")).strip()
    approved_ids = set(review.get("approved_sample_ids", []))
    if not reviewer or not role or not approved_ids:
        raise SystemExit("reviewer_name, reviewer_role and approved_sample_ids are required")
    records = {}
    for path in (DATA / "processed" / "conversations").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line); records[row["sample_id"]] = row
    unknown = approved_ids - set(records)
    if unknown: raise SystemExit(f"Unknown sample IDs: {sorted(unknown)}")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    output_by_id = {}
    target = DATA / "approved" / "sft" / "reviewed_sft.jsonl"
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing = json.loads(line)
                output_by_id[existing["sample_id"]] = existing
    for sample_id in sorted(approved_ids):
        row = records[sample_id]
        output_by_id[sample_id] = {**row, "review_status": "APPROVED", "reviewer_name": reviewer, "reviewer_role": role, "reviewed_at": reviewed_at}
    output = [output_by_id[sample_id] for sample_id in sorted(output_by_id)]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output), encoding="utf-8")
    print(f"approved_sft_samples_total={len(output)} newly_reviewed_or_updated={len(approved_ids)} reviewer={reviewer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
