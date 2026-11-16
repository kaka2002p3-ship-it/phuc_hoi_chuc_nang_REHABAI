from __future__ import annotations

import math
from fastapi.testclient import TestClient

from backend.deep_breathing.analyzer import BreathingAnalyzer
from backend.deep_breathing.config import DeepBreathingConfig
from backend.deep_breathing.signal import MotionSignalProcessor
from backend.deep_breathing.state_machine import BreathingStateMachine
from backend.deep_breathing.types import BreathPhase, PoseFrame, TrackingQuality
from backend.main import app
from test_helpers import auth


def pose(y: float = 0.45, visibility: float = 0.95, x_shift: float = 0.0) -> PoseFrame:
    return PoseFrame(
        left_shoulder=(0.40 + x_shift, y, 0.0), right_shoulder=(0.60 + x_shift, y, 0.0),
        left_visibility=visibility, right_visibility=visibility,
        left_hip=(0.43 + x_shift, 0.80, 0.0), right_hip=(0.57 + x_shift, 0.80, 0.0),
        nose=(0.50 + x_shift, 0.25, 0.0),
    )


def test_signal_uses_visibility_calibration_ema_and_outlier_gate():
    config = DeepBreathingConfig(max_normalized_jump=0.08)
    processor = MotionSignalProcessor(config)
    assert processor.calibrate([pose(), pose(0.451), pose(0.449)])
    sample = processor.update(pose(0.43))
    assert sample.valid and sample.signal is not None
    assert processor.update(pose(0.10)).outlier
    assert processor.update(pose(visibility=0.1)).tracking_quality == TrackingQuality.POOR


def test_calibration_rejects_insufficient_good_frame_ratio():
    processor = MotionSignalProcessor(DeepBreathingConfig(min_good_frames_ratio=0.7))
    assert not processor.calibrate([pose(), pose(visibility=0.1), pose(visibility=0.1)])
    assert not processor.calibrated


def test_state_machine_blocks_invalid_exhale_to_inhale_transition():
    machine = BreathingStateMachine(DeepBreathingConfig())
    assert machine.transition(BreathPhase.READY)
    assert machine.transition(BreathPhase.INHALE)
    assert machine.transition(BreathPhase.EXHALE)
    assert not machine.transition(BreathPhase.INHALE)


def test_analyzer_timer_guidance_counts_one_cycle_without_claiming_clinical_correctness():
    config = DeepBreathingConfig(inhale_seconds=1, exhale_seconds=1, calibration_seconds=0.2, target_cycles=2, min_cycle_seconds=1,
                                 rise_threshold=0.001, fall_threshold=-0.001, neutral_threshold=0.0002, min_phase_frames=2)
    analyzer = BreathingAnalyzer(config)
    updates = []
    for index in range(0, 25):
        timestamp = index * 0.1
        y = 0.45 - 0.02 * math.sin(timestamp * math.pi)
        updates.append(analyzer.update(pose(y), timestamp))
    assert analyzer.completed_cycles >= 1
    assert all(update.phase != BreathPhase.COMPLETED or update.completed_cycles == config.target_cycles for update in updates)


def test_static_signal_does_not_create_fake_cycle():
    config = DeepBreathingConfig(inhale_seconds=1, exhale_seconds=1, calibration_seconds=0.2, target_cycles=2, min_cycle_seconds=1,
                                 rise_threshold=0.001, fall_threshold=-0.001, neutral_threshold=0.0002, min_phase_frames=2)
    analyzer = BreathingAnalyzer(config)
    for index in range(0, 45):
        analyzer.update(pose(0.45), index * 0.1)
    assert analyzer.completed_cycles == 0
    assert analyzer.interrupted_cycles >= 1


def test_synthetic_gaps_spikes_and_body_shift_are_conservative():
    config = DeepBreathingConfig(short_gap_frames=1, long_gap_frames=3, max_normalized_jump=0.05, body_motion_threshold=0.08)
    processor = MotionSignalProcessor(config)
    assert processor.calibrate([pose(), pose(), pose()])
    processor.update(pose(0.44))
    assert processor.update(pose(0.20)).outlier
    assert processor.update(pose(0.44, x_shift=0.12)).artifact_detected
    assert not processor.update(pose(visibility=0.1)).valid
    assert processor.update(pose(visibility=0.1)).tracking_quality == TrackingQuality.POOR
    assert processor.update(pose(visibility=0.1)).tracking_quality == TrackingQuality.UNAVAILABLE


def test_normalized_trend_direction_matches_shoulder_motion():
    config = DeepBreathingConfig(ema_alpha=1.0, max_normalized_jump=1.0, min_phase_frames=2)
    processor = MotionSignalProcessor(config)
    processor.calibrate([pose(), pose(), pose()])
    processor.update(pose(0.45))
    rising = processor.update(pose(0.43))
    falling = processor.update(pose(0.47))
    assert rising.velocity is not None and rising.velocity > 0
    assert falling.velocity is not None and falling.velocity < 0


def test_long_tracking_gap_is_not_incorrect_rep():
    config = DeepBreathingConfig(calibration_seconds=0.1, short_gap_frames=1, long_gap_frames=3)
    analyzer = BreathingAnalyzer(config)
    analyzer.update(pose(), 0)
    analyzer.update(pose(), 0.2)
    for index in range(1, 4):
        update = analyzer.update(pose(visibility=0.1), 0.2 + index * 0.1)
    assert update.phase == BreathPhase.TRACKING_INSUFFICIENT
    assert update.tracking_quality in {TrackingQuality.POOR, TrackingQuality.UNAVAILABLE}


def test_deep_breathing_sessions_are_authenticated_and_private():
    client = TestClient(app)
    owner = auth(client)
    other = auth(client)
    created = client.post("/api/deep-breathing/sessions", headers=owner, json={})
    assert created.status_code == 201
    session_id = created.json()["session_id"]
    assert client.get(f"/api/deep-breathing/sessions/{session_id}", headers=owner).status_code == 200
    assert client.get(f"/api/deep-breathing/sessions/{session_id}", headers=other).status_code == 404
    finished = client.post(
        f"/api/deep-breathing/sessions/{session_id}/finish",
        headers=owner,
        json={"session_status": "COMPLETED", "tracking_mode": "GUIDED_TIMER_ONLY", "guided_cycles_completed": 2},
    )
    assert finished.status_code == 200
    assert finished.json()["tracking_quality"] == "UNAVAILABLE"
    assert finished.json()["session_status"] == "COMPLETED"
    assert client.post(f"/api/deep-breathing/sessions/{session_id}/finish", headers=owner, json={"session_status": "CANCELLED"}).status_code == 200


def test_invalid_combined_protocol_is_rejected_as_validation_error():
    client = TestClient(app)
    headers = auth(client)
    response = client.post("/api/deep-breathing/sessions", headers=headers, json={"inhale_seconds": 10, "exhale_seconds": 15})
    assert response.status_code == 422


def test_deep_breathing_api_requires_authentication():
    client = TestClient(app)
    assert client.get("/api/deep-breathing/config").status_code == 401
    assert client.post("/api/deep-breathing/sessions", json={}).status_code == 401


def test_timer_only_is_truthfully_marked_unavailable():
    analyzer = BreathingAnalyzer(DeepBreathingConfig(inhale_seconds=2, exhale_seconds=2, target_cycles=2))
    update = analyzer.timer_only_update(4.1)
    assert update.completed_cycles == 1
    assert update.tracking_quality == TrackingQuality.UNAVAILABLE
    assert update.confidence == "UNKNOWN"


def test_deep_breathing_websocket_rejects_foreign_owner():
    client = TestClient(app)
    owner = auth(client)
    other = auth(client)
    session_id = client.post("/api/deep-breathing/sessions", headers=owner, json={}).json()["session_id"]
    other_token = other["Authorization"].split(" ", 1)[1]
    try:
        with client.websocket_connect(f"/ws/deep-breathing/{session_id}?token={other_token}") as websocket:
            websocket.receive_json()
        assert False, "foreign user WebSocket must close"
    except Exception:
        pass
