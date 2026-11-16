"""Fail closed when local AI corpus violates provenance/review boundaries."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_ai"
ALLOWED_STATUS = {"RAW", "CLEANED", "REVIEWED", "APPROVED", "REJECTED"}
REQUIRED_SAMPLE = {"sample_id", "domain", "intent", "language", "messages", "source", "review_status"}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError as exc: raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
    return rows


def main() -> int:
    errors: list[str] = []
    conversations: list[dict] = []
    for path in sorted((DATA / "processed" / "conversations").glob("*.jsonl")):
        try: rows = read_jsonl(path)
        except ValueError as exc: errors.append(str(exc)); continue
        for row in rows:
            missing = REQUIRED_SAMPLE - set(row)
            if missing: errors.append(f"{path.name}:{row.get('sample_id')}: missing {sorted(missing)}")
            if row.get("review_status") not in ALLOWED_STATUS: errors.append(f"{path.name}:{row.get('sample_id')}: invalid review status")
            messages = row.get("messages", [])
            if len(messages) < 2 or messages[0].get("role") != "user" or messages[-1].get("role") != "assistant": errors.append(f"{path.name}:{row.get('sample_id')}: invalid turns")
            conversations.append(row)
    user_keys = []
    for row in conversations:
        first = next((m.get("content", "") for m in row.get("messages", []) if m.get("role") == "user"), "")
        user_keys.append(" ".join(first.casefold().split()))
    duplicates = [key for key, count in Counter(user_keys).items() if key and count > 1]
    if duplicates: errors.append(f"duplicate user prompts across splits: {duplicates[:5]}")
    training_prompts = set(user_keys)
    for path in sorted((DATA / "processed" / "evaluation").glob("*.jsonl")):
        for row in read_jsonl(path):
            if not row.get("excluded_from_training"):
                errors.append(f"{path.name}:{row.get('eval_id')}: eval must be excluded from training")
            if row.get("review_status") == "APPROVED":
                errors.append(f"{path.name}:{row.get('eval_id')}: pending eval unexpectedly approved")
            key = " ".join(str(row.get("user_text", "")).casefold().split())
            if key in training_prompts:
                errors.append(f"{path.name}:{row.get('eval_id')}: evaluation leakage into conversation splits")
    for path in sorted((DATA / "approved" / "sft").glob("*.jsonl")):
        for row in read_jsonl(path):
            if row.get("review_status") != "APPROVED": errors.append(f"{path.name}: non-approved item in approved/sft")
    for path in sorted((DATA / "approved" / "rag").glob("*.jsonl")):
        for row in read_jsonl(path):
            if row.get("review_status") != "APPROVED" or not row.get("source_id"): errors.append(f"{path.name}: invalid approved RAG item")
    print(f"conversation_samples={len(conversations)} errors={len(errors)}")
    for error in errors: print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
