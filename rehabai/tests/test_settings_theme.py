import uuid

from fastapi.testclient import TestClient

from backend.main import app


def test_settings_accept_system_theme():
    client = TestClient(app)
    response = client.post("/api/auth/register", json={
        "email": f"theme-{uuid.uuid4()}@example.com",
        "full_name": "Theme Tester",
        "password": "safe-password-123",
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "language": "vi",
        "pain_alerts": True,
        "practice_reminders": True,
        "theme": "system",
        "camera_resolution": "1280x720",
    }
    saved = client.put("/api/settings", headers=headers, json=payload)
    assert saved.status_code == 200
    assert saved.json()["theme"] == "system"
    loaded = client.get("/api/settings", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json() == payload
