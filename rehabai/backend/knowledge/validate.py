"""Validate approved knowledge metadata, hashes and expiry before release."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .retriever import APPROVED_DIR, METADATA_DIR, load_approved

HEX64 = re.compile(r"^[a-f0-9]{64}$")

def main() -> int:
    errors: list[str] = []
    documents = sorted(APPROVED_DIR.glob("*.md")) if APPROVED_DIR.exists() else []
    for document in documents:
        metadata_path = METADATA_DIR / f"{document.stem}.json"
        if not metadata_path.exists():
            errors.append(f"missing metadata: {document.name}")
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid metadata {metadata_path.name}: {exc}")
            continue
        if metadata.get("approval_status") != "approved" or metadata.get("review_status") != "approved":
            errors.append(f"not approved: {document.name}")
        digest = __import__("hashlib").sha256(document.read_bytes()).hexdigest()
        if not HEX64.fullmatch(str(metadata.get("content_hash", ""))) or metadata.get("content_hash") != digest:
            errors.append(f"content hash mismatch: {document.name}")
    chunks, version = load_approved()
    print(f"documents={len(documents)} approved_chunks={len(chunks)} knowledge_version={version}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
