import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import app
from test_helpers import auth


def test_websocket_rejects_missing_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/inference"):
            pass
    assert error.value.code == 1008


def test_websocket_accepts_authenticated_user():
    client = TestClient(app)
    token = auth(client)["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/ws/inference?token={token}") as websocket:
        websocket.send_text("not-json")
        assert websocket.receive_json()["error"] == "Invalid JSON format"
