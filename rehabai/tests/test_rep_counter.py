import numpy as np
import pytest

from backend.core.rep_counter import RuleBasedRepCounter, THRESHOLDS


@pytest.mark.parametrize("exercise_id", [2, 3, 4])
def test_full_high_low_cycle_counts_once(exercise_id):
    counter = RuleBasedRepCounter(exercise_id, confirm_frames=3, cooldown_s=0)
    threshold = THRESHOLDS[exercise_id]
    values = iter([threshold.low - 1] * 5 + [threshold.high + 1] * 7 + [threshold.low - 1] * 7)
    counter._signal = lambda *_: next(values)
    pose = np.ones((33, 3), dtype=np.float32)
    for _ in range(19):
        result = counter.update(pose, None, None, quality_ready=True)
    assert result["rep_count"] == 1
    assert result["estimated"] is True


def test_shoulder_uses_low_active_direction():
    counter = RuleBasedRepCounter(1, confirm_frames=2, cooldown_s=0)
    threshold = THRESHOLDS[1]
    values = iter([threshold.high + 5] * 4 + [threshold.low - 2] * 5 + [threshold.high + 5] * 5)
    counter._signal = lambda *_: next(values)
    pose = np.ones((33, 3), dtype=np.float32)
    for _ in range(14):
        result = counter.update(pose, None, None, quality_ready=True)
    assert result["rep_count"] == 1


def test_missing_landmarks_never_counts():
    counter = RuleBasedRepCounter(2, confirm_frames=1, cooldown_s=0)
    counter._signal = lambda *_: 180.0
    pose = np.ones((33, 3), dtype=np.float32)
    for _ in range(10):
        result = counter.update(pose, None, None, quality_ready=False)
    assert result["rep_count"] == 0
    assert result["quality_ready"] is False


def test_noise_between_thresholds_does_not_count():
    counter = RuleBasedRepCounter(2, confirm_frames=2, cooldown_s=0)
    values = iter([100.0, 120.0, 130.0, 110.0] * 4)
    counter._signal = lambda *_: next(values)
    pose = np.ones((33, 3), dtype=np.float32)
    for _ in range(16):
        counter.update(pose, None, None, quality_ready=True)
    assert counter.rep_count == 0
