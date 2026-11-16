from fastapi.testclient import TestClient

from backend.main import app
from test_helpers import auth


def test_export_and_delete_my_data():
    client = TestClient(app)
    headers = auth(client)
    started = client.post("/api/exercise/session/start", json={"exercise_id": 2, "target_reps": 3, "pain_before": 1}, headers=headers)
    assert started.status_code == 200
    exported = client.get("/api/users/me/export", headers=headers)
    assert exported.status_code == 200
    assert any(item["id"] == started.json()["session_id"] for item in exported.json()["sessions"])
    deleted = client.delete("/api/users/me", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/users/me", headers=headers).status_code == 401
