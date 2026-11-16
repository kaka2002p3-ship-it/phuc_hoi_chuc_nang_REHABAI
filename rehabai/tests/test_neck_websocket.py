import base64

import cv2
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from test_helpers import auth


class DummyExtractor:
    def __init__(self, *args, **kwargs):
        self.pose = np.zeros((33, 3), dtype=np.float32)

    def process_frame(self, image):
        return None

    def quality_status(self, *args, **kwargs):
        return {"ready": False, "code": "insufficient_landmarks"}

    def get_skeleton(self):
        return {"pose": self.pose.tolist(), "left_hand": [], "right_hand": []}


@patch("backend.api.websocket.RealtimeExtractor", DummyExtractor)
def test_neck_session_websocket_does_not_crash_on_first_frame():
    client = TestClient(app)
    headers = auth(client)
    token = headers["Authorization"].split(" ", 1)[1]
    started = client.post(
        "/api/exercise/session/start",
        json={"exercise_id": 6, "target_reps": 2, "pain_before": 0},
        headers=headers,
    )
    assert started.status_code == 200
    session_id = started.json()["session_id"]
    ok, encoded = cv2.imencode(".jpg", np.zeros((120, 160, 3), dtype=np.uint8))
    assert ok
    frame = base64.b64encode(encoded.tobytes()).decode("ascii")

    with client.websocket_connect(f"/ws/exercise/{session_id}?token={token}") as websocket:
        websocket.send_json({"timestamp": 1000, "frame": frame})
        payload = websocket.receive_json()
        assert payload["rep"]["rep_count"] == 0
        assert payload["quality"]["ready"] is False
