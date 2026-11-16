from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Intent = Literal[
    "GENERAL_CHAT", "EMOTIONAL_SUPPORT", "NUTRITION_GENERAL", "EXERCISE_GUIDANCE",
    "LIVE_SESSION_EXPLANATION", "SESSION_SUMMARY", "PROGRESS_REVIEW", "PAIN_REPORT",
    "TECHNICAL_SUPPORT", "SAFETY_SUPPORT",
]


class LLMReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["vi", "en"]
    intent: Intent
    evidence_ids: list[str] = Field(default_factory=list, max_length=16)
    needs_clarification: bool = False


def parse_llm_reply(raw: str, valid_evidence: set[str]) -> LLMReply | None:
    import json
    try:
        value = json.loads(raw)
        reply = LLMReply.model_validate(value)
        if any(item not in valid_evidence for item in reply.evidence_ids):
            return None
        return reply
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
