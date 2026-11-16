from fastapi.testclient import TestClient

from backend.chatbot.ollama_client import chat
from backend.chatbot.safety import safety_reply
from backend.chatbot.schemas import LLMReply
from backend.main import app
from test_helpers import auth


def test_safety_matches_unaccented_vietnamese_and_preserves_english():
    crisis = safety_reply("toi muon tu lam hai ban than", "vi")
    assert crisis and crisis[1] == "SAFETY_SUPPORT"
    english = safety_reply("I have chest pain", "en")
    assert english and english[1] == "SAFETY_SUPPORT"
    assert english[0].startswith("This may be an emergency")


def test_normal_sadness_is_not_crisis():
    assert safety_reply("I feel sad and frustrated today", "en") is None


def test_model_unavailable_status_is_explicit(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")
    result, status = chat([{"role": "user", "content": "hello"}], set())
    assert result is None
    assert status == "TIMEOUT_OR_UNAVAILABLE"


def test_explicit_language_mismatch_is_not_accepted(monkeypatch):
    from backend.api import chat as api_chat
    monkeypatch.setattr(api_chat, "_ollama_call", lambda *_: (LLMReply(
        message="Xin chào", language="vi", intent="GENERAL_CHAT", evidence_ids=[], needs_clarification=False
    ), "ready"))
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "Hello", "language": "en"}, headers=auth(client))
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local_fallback"
    assert body["assistant_status"] == "INVALID_MODEL_OUTPUT"
    assert body["assistant"]["language"] == "en"


def test_auto_vietnamese_rejects_cjk_content(monkeypatch):
    from backend.api import chat as api_chat
    monkeypatch.setattr(api_chat, "_ollama_call", lambda *_: (LLMReply(
        message="Chào bạn! 今天天气不错。", language="vi", intent="GENERAL_CHAT",
        evidence_ids=[], needs_clarification=False
    ), "ready"))
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "chào bạn", "language": "auto"}, headers=auth(client))
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_status"] == "INVALID_MODEL_OUTPUT"
    assert body["assistant"]["language"] == "vi"
    assert not api_chat._has_cjk(body["assistant"]["message"])
