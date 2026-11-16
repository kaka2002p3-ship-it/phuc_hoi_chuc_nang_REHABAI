import numpy as np

from backend.core.neck_lateral_stretch import NeckLateralStretchCounter, relative_head_tilt, normalize_angle


def pose(angle=0.0):
    p = np.zeros((33, 3), dtype=np.float32)
    # horizontal shoulders; ears move vertically to encode lateral tilt
    p[11, :2] = [0.35, 0.55]; p[12, :2] = [0.65, 0.55]
    p[7, :2] = [0.45, 0.35]; p[8, :2] = [0.55, 0.35 + np.tan(np.deg2rad(angle)) * 0.1]
    return p


def test_angle_sign_and_normalize():
    assert relative_head_tilt(pose(-20)) > 0
    assert relative_head_tilt(pose(20)) < 0
    assert normalize_angle(181) == -179


def test_neck_requires_hold_and_return():
    c = NeckLateralStretchCounter({"hold_seconds": 1.0})
    assert c.calibrate([pose() for _ in range(20)])
    t = 0.0
    for _ in range(12): c.update(pose(-20), t := t + .1)
    for _ in range(20): c.update(pose(-20), t := t + .1)
    assert c.rep_count == 0
    for _ in range(20): c.update(pose(), t := t + .1)
    assert c.rep_count == 1


def test_tracking_loss_interrupts_rep_and_requires_center_recovery():
    c = NeckLateralStretchCounter({"hold_seconds": 0.2, "long_gap_frames": 2})
    assert c.calibrate([pose() for _ in range(20)])
    t = 0.0
    for _ in range(8): c.update(pose(20), t := t + .1)
    for _ in range(3): c.update(pose(20), t := t + .1, quality_ready=False)
    assert c.state == "TRACKING_INSUFFICIENT"
    assert c.interrupted_reps == 1
    for _ in range(10): c.update(pose(), t := t + .1)
    assert c.state == "CENTER"
    assert c.rep_count == 0


def test_target_jump_before_minimum_phase_does_not_start_hold():
    c = NeckLateralStretchCounter({"min_phase_ms": 500})
    assert c.calibrate([pose() for _ in range(20)])
    c.update(pose(-20), 0.1)
    update = c.update(pose(-20), 0.2)
    assert update["state"] == "MOVING_RIGHT"
    assert update["rep_count"] == 0
