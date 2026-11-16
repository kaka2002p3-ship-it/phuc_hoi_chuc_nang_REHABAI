"""Apply explicit APPROVED/REJECTED decisions from a reviewer CSV queue."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_ai"
ALLOWED = {"PENDING", "APPROVED", "REJECTED"}


def load_samples() -> dict[str, dict]:
    samples: dict[str, dict] = {}
    for path in (DATA / "processed" / "conversations").glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                samples[row["sample_id"]] = row
    return samples


def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {row["sample_id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def write_rows(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(rows[key], ensure_ascii=False) + "\n" for key in sorted(rows)), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewer-role", required=True)
    args = parser.parse_args()
    queue = Path(args.queue).resolve()
    if not queue.exists():
        raise SystemExit(f"Review queue not found: {queue}")
    samples = load_samples()
    approved_path = DATA / "approved" / "sft" / "reviewed_sft.jsonl"
    rejected_path = DATA / "rejected" / "reviewed_conversations.jsonl"
    approved = load_existing(approved_path); rejected = load_existing(rejected_path)
    reviewed_at = datetime.now(timezone.utc).isoformat()
    applied_approved = applied_rejected = pending = 0
    with queue.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sample_id = str(row.get("sample_id", "")).strip()
            decision = str(row.get("decision", "PENDING")).strip().upper()
            queue_reviewer = str(row.get("reviewer", "")).strip()
            if queue_reviewer and queue_reviewer != args.reviewer:
                raise SystemExit(f"Reviewer mismatch for {sample_id}: {queue_reviewer} != {args.reviewer}")
            if decision not in ALLOWED:
                raise SystemExit(f"Invalid decision for {sample_id}: {decision}")
            if sample_id not in samples:
                raise SystemExit(f"Unknown sample ID: {sample_id}")
            if decision == "PENDING":
                pending += 1; continue
            reviewed = {**samples[sample_id], "review_status": decision, "reviewer_name": args.reviewer, "reviewer_role": args.reviewer_role, "reviewed_at": reviewed_at, "review_notes": str(row.get("review_notes", "")).strip()}
            if decision == "APPROVED":
                approved[sample_id] = reviewed; rejected.pop(sample_id, None); applied_approved += 1
            else:
                rejected[sample_id] = reviewed; approved.pop(sample_id, None); applied_rejected += 1
    write_rows(approved_path, approved)
    write_rows(rejected_path, rejected)
    print(f"reviewer={args.reviewer} approved_applied={applied_approved} rejected_applied={applied_rejected} pending={pending} approved_total={len(approved)} rejected_total={len(rejected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
