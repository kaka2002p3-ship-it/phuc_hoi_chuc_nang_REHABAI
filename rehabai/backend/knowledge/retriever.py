"""Dependency-free approved knowledge retriever for the local Ollama assistant."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
APPROVED_DIR = ROOT / "approved"
METADATA_DIR = ROOT / "metadata"
TOKEN_RE = re.compile(r"[\wÀ-ỹ]{2,}", re.UNICODE)
MAX_RESULTS = 4
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP = 120

def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))

def _tokens(value: str) -> set[str]:
    return set(TOKEN_RE.findall(_fold(value)))

def _expired(metadata: dict[str, Any]) -> bool:
    expires_at = metadata.get("expires_at")
    if not expires_at:
        return False
    try:
        value = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value <= datetime.now(timezone.utc)
    except ValueError:
        return True

def _chunks(text: str) -> list[str]:
    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + MAX_CHUNK_CHARS)
        if end < len(cleaned):
            boundary = max(cleaned.rfind("\n\n", start, end), cleaned.rfind(". ", start, end))
            if boundary > start + MAX_CHUNK_CHARS // 2:
                end = boundary + (2 if cleaned[boundary:boundary + 2] == ". " else 0)
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks

@dataclass(frozen=True)
class KnowledgeChunk:
    evidence_id: str
    document_id: str
    title: str
    source: str
    scope: tuple[str, ...]
    content: str
    score: float

def load_approved() -> tuple[list[KnowledgeChunk], str]:
    documents: list[KnowledgeChunk] = []
    version_parts: list[str] = []
    if not APPROVED_DIR.exists():
        return [], "none-unapproved"
    for document in sorted(APPROVED_DIR.glob("*.md")):
        metadata_path = METADATA_DIR / f"{document.stem}.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get("approval_status") != "approved" or metadata.get("review_status", "approved") != "approved" or _expired(metadata):
            continue
        digest = hashlib.sha256(document.read_bytes()).hexdigest()
        if digest != metadata.get("content_hash"):
            continue
        document_id = str(metadata.get("document_id") or document.stem)
        title = str(metadata.get("title") or document_id)
        source = str(metadata.get("source") or "internal")
        scope = tuple(str(item) for item in metadata.get("scope", []))
        version_parts.append(f"{document_id}:{metadata.get('version')}:{digest}")
        for index, content in enumerate(_chunks(document.read_text(encoding="utf-8"))):
            documents.append(KnowledgeChunk(f"knowledge_{document_id}_{index + 1}", document_id, title, source, scope, content, 0.0))
    if not version_parts:
        return [], "none-unapproved"
    version = hashlib.sha256("|".join(version_parts).encode("utf-8")).hexdigest()[:16]
    return documents, f"approved-{version}"

def retrieve(query: str, *, scopes: set[str] | None = None, limit: int = MAX_RESULTS) -> tuple[list[dict[str, Any]], set[str], str]:
    chunks, version = load_approved()
    if not chunks or not query.strip():
        return [], set(), version
    query_tokens = _tokens(query)
    ranked: list[KnowledgeChunk] = []
    for chunk in chunks:
        if scopes and not (set(chunk.scope) & scopes):
            continue
        overlap = len(query_tokens & _tokens(chunk.content))
        title_overlap = len(query_tokens & _tokens(chunk.title))
        score = overlap + (title_overlap * 1.5)
        if score > 0:
            ranked.append(KnowledgeChunk(chunk.evidence_id, chunk.document_id, chunk.title, chunk.source, chunk.scope, chunk.content, score))
    ranked.sort(key=lambda item: (-item.score, item.document_id, item.evidence_id))
    selected = ranked[: max(1, min(limit, MAX_RESULTS))]
    payload = [{"evidence_id": item.evidence_id, "document_id": item.document_id, "title": item.title, "source": item.source, "scope": list(item.scope), "content": item.content, "review_status": "approved"} for item in selected]
    return payload, {item["evidence_id"] for item in payload}, version
