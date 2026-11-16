from fastapi.testclient import TestClient
from backend.main import app
from test_helpers import auth

def test_session_start_end_history():
    client=TestClient(app); headers=auth(client); started=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":6,"pain_before":1},headers=headers)
    assert started.status_code==200; sid=started.json()["session_id"]
    ended=client.post("/api/exercise/session/end",json={"session_id":sid,"repetition":6,"pain_after":1},headers=headers)
    assert ended.status_code==200 and ended.json()["repetition"]==6
    assert ended.json()["status"] == "COMPLETED"
    item = next(item for item in client.get("/api/exercise/history",headers=headers).json() if item["id"]==sid)
    assert item["status"] == "COMPLETED" and item["repetition"] == 6 and item["target_reps"] == 6

def test_session_stopped_before_target_is_incomplete():
    client=TestClient(app); headers=auth(client)
    started=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":6,"pain_before":1},headers=headers)
    sid=started.json()["session_id"]
    ended=client.post("/api/exercise/session/end",json={"session_id":sid,"repetition":2,"pain_after":1},headers=headers)
    assert ended.status_code == 200
    assert ended.json()["status"] == "INCOMPLETE"
    item = next(item for item in client.get("/api/exercise/history",headers=headers).json() if item["id"] == sid)
    assert item["status"] == "INCOMPLETE"
    assert item["repetition"] == 2 and item["target_reps"] == 6
    summary = client.get("/api/reports/summary",headers=headers).json()
    assert summary["total_sessions"] == 1
    assert summary["completed_sessions"] == 0
    assert summary["completion_rate"] == 0

def test_sessions_are_private_to_their_owner():
    client=TestClient(app); owner=auth(client); other=auth(client)
    sid=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":3},headers=owner).json()["session_id"]
    assert any(item["id"]==sid for item in client.get("/api/exercise/history",headers=owner).json())
    assert all(item["id"]!=sid for item in client.get("/api/exercise/history",headers=other).json())
    assert client.post("/api/exercise/session/end",json={"session_id":sid,"repetition":1,"pain_after":1},headers=other).status_code==404
    assert client.get(f"/api/exercise/history/{sid}",headers=other).status_code==404

def test_session_detail_lists_repetitions():
    client=TestClient(app); headers=auth(client)
    sid=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":3},headers=headers).json()["session_id"]
    client.post("/api/exercise/session/end",json={"session_id":sid,"repetition":2,"pain_after":1},headers=headers)
    detail=client.get(f"/api/exercise/history/{sid}",headers=headers)
    assert detail.status_code == 200
    assert [row["repetition_number"] for row in detail.json()["repetitions"]] == [1, 2]
    assert detail.json()["unassessed_reps"] == 2
    assert detail.json()["matched_reps"] == 0
    assert detail.json()["mismatched_reps"] == 0
    assert all(row["result"] == "unassessed" for row in detail.json()["repetitions"])

def test_session_end_requires_authentication():
    client=TestClient(app)
    assert client.post("/api/exercise/session/end",json={"session_id":"missing","repetition":0,"pain_after":0}).status_code==401

def test_pain_six_can_start_but_pain_seven_is_blocked():
    client=TestClient(app); headers=auth(client)
    allowed=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":5,"pain_before":6},headers=headers)
    assert allowed.status_code == 200
    blocked=client.post("/api/exercise/session/start",json={"exercise_id":4,"target_reps":5,"pain_before":7},headers=headers)
    assert blocked.status_code == 422
    assert "bác sĩ" in blocked.json()["detail"]
