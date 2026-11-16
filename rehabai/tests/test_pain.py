from fastapi.testclient import TestClient
from backend.main import app
from test_helpers import auth

def test_pain_increase_warning():
    client=TestClient(app); headers=auth(client); started=client.post("/api/exercise/session/start",json={"exercise_id":2,"target_reps":5},headers=headers)
    sid=started.json()["session_id"]
    assert client.post("/api/pain/before",json={"session_id":sid,"pain_score":2},headers=headers).status_code==200
    after=client.post("/api/pain/after",json={"session_id":sid,"pain_score":5},headers=headers)
    assert after.status_code==200 and after.json()["warning"] is True and after.json()["pain_increase"] is True
