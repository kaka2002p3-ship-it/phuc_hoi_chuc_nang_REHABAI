import json
import io
from fastapi.testclient import TestClient

from backend.chatbot.prompts import MASTER, PACKAGED_PROMPT, _extract_master_prompt, load_system_prompt
from backend.chatbot.schemas import parse_llm_reply
from backend.chatbot.safety import safety_reply
from backend.main import app
from backend.chatbot.ollama_client import chat as ollama_chat
from backend.chatbot.context import build_context
from backend.core.db import SessionLocal, User
from test_helpers import auth


def test_master_system_prompt_is_loaded_verbatim():
    prompt = load_system_prompt()
    assert prompt.startswith("Bạn là RehabAI Companion")
    assert "HAND_OPENING" in prompt and "ELBOW_EXTENSION" in prompt
    assert "Vai - Nâng vật" not in prompt


def test_packaged_prompt_matches_master_when_source_is_available():
    assert PACKAGED_PROMPT.exists()
    if MASTER.exists():
        assert PACKAGED_PROMPT.read_text(encoding="utf-8").strip() == _extract_master_prompt()


def test_structured_output_rejects_unknown_evidence():
    raw = json.dumps({"message":"x","language":"vi","intent":"SESSION_SUMMARY","evidence_ids":["fake"],"needs_clarification":False})
    assert parse_llm_reply(raw, {"real"}) is None


def test_chat_safety_bypasses_ollama(monkeypatch):
    monkeypatch.setattr("backend.api.chat.ollama_chat", lambda *_: (_ for _ in ()).throw(AssertionError("must not call Ollama")))
    client=TestClient(app); headers=auth(client)
    response=client.post("/api/chat",json={"message":"Tôi muốn tự làm hại bản thân"},headers=headers)
    assert response.status_code==200
    assert response.json()["provider"]=="safety"
    assert response.json()["assistant"]["intent"]=="SAFETY_SUPPORT"


def test_chat_fallback_is_explicit(monkeypatch):
    monkeypatch.setattr("backend.api.chat.ollama_chat", lambda *_: (None,"MODEL_UNAVAILABLE"))
    client=TestClient(app); headers=auth(client)
    response=client.post("/api/chat",json={"message":"hello","language":"en"},headers=headers)
    body=response.json()
    assert body["provider"]=="local_fallback" and body["assistant_status"]=="MODEL_UNAVAILABLE"
    assert body["assistant"]["language"]=="en"


def test_chat_conversation_ownership(monkeypatch):
    monkeypatch.setattr("backend.api.chat.ollama_chat", lambda *_: (None,"MODEL_UNAVAILABLE"))
    client=TestClient(app); owner=auth(client); other=auth(client)
    created=client.post("/api/chat",json={"message":"xin chào"},headers=owner).json()
    cid=created["conversation_id"]
    assert client.get(f"/api/chat/conversations/{cid}",headers=owner).status_code==200
    assert client.get(f"/api/chat/conversations/{cid}",headers=other).status_code==404


def test_chat_rejects_other_users_session(monkeypatch):
    monkeypatch.setattr("backend.api.chat.ollama_chat", lambda *_: (None,"MODEL_UNAVAILABLE"))
    client=TestClient(app); owner=auth(client); other=auth(client)
    sid=client.post("/api/exercise/session/start",json={"exercise_id":2,"target_reps":3},headers=owner).json()["session_id"]
    assert client.post("/api/chat",json={"message":"tóm tắt","session_id":sid},headers=other).status_code==404


def test_history_rag_contains_only_authenticated_users_sessions():
    client=TestClient(app); owner=auth(client); other=auth(client)
    owner_sid=client.post("/api/exercise/session/start",json={"exercise_id":2,"target_reps":3},headers=owner).json()["session_id"]
    other_sid=client.post("/api/exercise/session/start",json={"exercise_id":2,"target_reps":4},headers=other).json()["session_id"]
    owner_email=client.get("/api/users/me",headers=owner).json()["email"]
    db=SessionLocal()
    try:
        user=db.query(User).filter(User.email==owner_email).first()
        context,evidence,error=build_context(db,user,None)
    finally:
        db.close()
    assert error is None
    session_ids={item["session_id"] for item in context["exercise_history"]}
    assert owner_sid in session_ids and other_sid not in session_ids
    assert f"session_{other_sid}" not in evidence


def test_ollama_request_uses_reply_json_schema(monkeypatch):
    captured = {}

    class FakeResponse(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *_): return False

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data.decode("utf-8")))
        return FakeResponse(json.dumps({"message":{"content":json.dumps({
            "message":"Chào bạn", "language":"vi", "intent":"GENERAL_CHAT",
            "evidence_ids":[], "needs_clarification":False,
        })}}).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result, status = ollama_chat([{"role":"user","content":"xin chào"}], set())
    assert status == "ready" and result is not None
    assert captured["format"]["additionalProperties"] is False
    assert set(captured["format"]["required"]) == {
        "message", "language", "intent", "evidence_ids", "needs_clarification",
    }
