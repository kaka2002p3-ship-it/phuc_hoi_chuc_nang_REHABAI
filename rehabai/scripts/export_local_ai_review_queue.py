"""Export a reviewer-friendly CSV without changing any approval state."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_ai"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--domains", default="software,conversation")
    args = parser.parse_args()
    domains = {item.strip() for item in args.domains.split(",") if item.strip()}
    approved = set()
    approved_file = DATA / "approved" / "sft" / "reviewed_sft.jsonl"
    if approved_file.exists():
        approved = {json.loads(line)["sample_id"] for line in approved_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    rows = []
    for path in sorted((DATA / "processed" / "conversations").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            item = json.loads(line)
            if item["domain"] not in domains or item["sample_id"] in approved: continue
            users = " | ".join(message["content"] for message in item["messages"] if message["role"] == "user")
            assistants = " | ".join(message["content"] for message in item["messages"] if message["role"] == "assistant")
            rows.append({"sample_id": item["sample_id"], "domain": item["domain"], "intent": item["intent"], "language": item["language"], "user_text": users, "assistant_response": assistants, "decision": "PENDING", "reviewer": args.reviewer, "review_notes": ""})
    target = DATA / "reports" / f"{args.reviewer}_review_queue.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["sample_id", "decision", "reviewer", "review_notes"])
        writer.writeheader(); writer.writerows(rows)
    print(f"review_queue={target} pending={len(rows)} reviewer={args.reviewer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
