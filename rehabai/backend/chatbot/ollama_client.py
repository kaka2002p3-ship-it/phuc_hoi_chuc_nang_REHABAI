from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .prompts import load_system_prompt
from .schemas import LLMReply, parse_llm_reply


_REPLY_FORMAT = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "minLength": 1, "maxLength": 4000},
        "language": {"type": "string", "enum": ["vi", "en"]},
        "intent": {
            "type": "string",
            "enum": [
                "GENERAL_CHAT", "EMOTIONAL_SUPPORT", "NUTRITION_GENERAL",
                "EXERCISE_GUIDANCE", "LIVE_SESSION_EXPLANATION",
                "SESSION_SUMMARY", "PROGRESS_REVIEW", "PAIN_REPORT",
                "TECHNICAL_SUPPORT", "SAFETY_SUPPORT",
            ],
        },
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
        "needs_clarification": {"type": "boolean"},
    },
    "required": ["message", "language", "intent", "evidence_ids", "needs_clarification"],
    "additionalProperties": False,
}


def ollama_enabled() -> bool:
    return os.getenv("OLLAMA_ENABLED", "1").strip().casefold() not in {"0", "false", "no", "off"}


def chat(messages: list[dict], valid_evidence: set[str], system_prompt: str | None = None) -> tuple[LLMReply | None, str]:
    if not ollama_enabled():
        return None, "MODEL_UNAVAILABLE"
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip() or "qwen2.5:7b"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt or load_system_prompt()}, *messages],
        "stream": False,
        # Ollama structured output prevents otherwise intermittent malformed
        # JSON from disabling an otherwise healthy local assistant.
        "format": _REPLY_FORMAT,
        "options": {"temperature": 0.3, "num_predict": 500},
        "keep_alive": "10m",
    }
    request = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        timeout = float(os.getenv("CHAT_REQUEST_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw = body.get("message", {}).get("content", "")
        parsed = parse_llm_reply(raw, valid_evidence)
        return (parsed, "ready" if parsed else "INVALID_MODEL_OUTPUT")
    except urllib.error.HTTPError as exc:
        # Ollama returns 404 for an uninstalled model; expose that state rather
        # than mislabeling it as a generic timeout.
        if exc.code == 404:
            return None, "MODEL_UNAVAILABLE"
        return None, "OLLAMA_ERROR"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
        return None, "TIMEOUT_OR_UNAVAILABLE"
