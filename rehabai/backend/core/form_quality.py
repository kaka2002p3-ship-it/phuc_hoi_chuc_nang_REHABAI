"""Rule-based form and pace checker for rule-counted exercises.

Complements the recognition-only ML model with two deterministic signals:

* **Amplitude / angle range** — how far the monitored joint angle (or hand-open
  ratio) actually moved during each repetition cycle. A cycle whose range is
  too small means the movement was performed with a short range of motion
  ("góc tập thiếu biên độ" = arm angle not fully correct).
* **Pace / speed** — the duration of each repetition cycle. Cycles that are
  much faster or slower than the recommended band are flagged as too quick or
  too slow, which matters for post-stroke upper-limb rehabilitation where
  slow, controlled movement is the therapeutic target.

No new model training is required; the thresholds derive from the existing
``RuleBasedRepCounter`` bands.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# Per-exercise ideal pace band in seconds per repetition cycle.
PACE_BANDS: dict[int, tuple[float, float]] = {
    1: (1.5, 8.0),   # shoulder elevation
    2: (1.5, 8.0),   # elbow flexion/extension
    3: (1.5, 8.0),   # forearm/wrist
    4: (1.0, 7.0),   # hand opening
    6: (1.5, 8.0),   # neck lateral stretch
}

# Minimum acceptable range of the monitored signal within one cycle.
# Angles are in degrees; the hand-open ratio is dimensionless.
MIN_RANGE: dict[int, float] = {
    1: 18.0,
    2: 25.0,
    3: 15.0,
    4: 0.18,
    6: 12.0,
}

PACE_LABELS = {
    "too_fast": "Tập nhanh hơn khuyến nghị — hãy tập chậm, kiểm soát chuyển động.",
    "ok": "Tốc độ phù hợp với khuyến nghị.",
    "too_slow": "Tập chậm hơn khuyến nghị — có thể tăng nhịp nhẹ, vẫn giữ kiểm soát.",
    "unknown": "Chưa đủ dữ liệu để đánh giá tốc độ.",
}

ANGLE_LABELS = {
    "ok": "Biên độ (góc) tập đạt mức khuyến nghị.",
    "short_range": "Biên độ góc quá nhỏ — động tác chưa đúng biên, hãy tập đầy đủ phạm vi chuyển động mà không đau.",
    "unknown": "Chưa đủ dữ liệu để đánh giá góc.",
}


@dataclass
class _CycleBuffer:
    start: float = 0.0
    samples: deque = field(default_factory=lambda: deque(maxlen=60))
    started: bool = False


@dataclass
class RepFormRecord:
    rep_number: int
    cycle_seconds: float | None
    signal_min: float | None
    signal_max: float | None
    pace: str
    angle: str


def _pace_verdict(cycle_seconds: float | None, exercise_id: int) -> str:
    if cycle_seconds is None:
        return "unknown"
    low, high = PACE_BANDS.get(exercise_id, (1.5, 8.0))
    if cycle_seconds < low * 0.75:
        return "too_fast"
    if cycle_seconds > high * 1.25:
        return "too_slow"
    return "ok"


def _angle_verdict(signal_min: float | None, signal_max: float | None, exercise_id: int) -> str:
    if signal_min is None or signal_max is None:
        return "unknown"
    span = abs(signal_max - signal_min)
    return "ok" if span >= MIN_RANGE.get(exercise_id, 15.0) else "short_range"


class FormQualityTracker:
    """Tracks per-repetition form (angle span) and pace for one session.

    The caller supplies the clock (``now``) on every :meth:`observe` call, so
    the tracker is agnostic to wall-clock vs. monotonic time. The cycle
    window is opened lazily on the first observation rather than at
    construction, which avoids mixing two different time bases.
    """

    def __init__(self, exercise_id: int):
        self.exercise_id = exercise_id
        self.records: list[RepFormRecord] = []
        self._buffer = _CycleBuffer(start=0.0, started=False)
        self._last_rep = 0

    def observe(self, now: float, rep_count: int, signal: float | None) -> list[RepFormRecord]:
        """Feed a new (time, rep_count, signal) sample; returns completed rep records.

        Samples with a non-positive timestamp are ignored: the caller passes
        wall-clock seconds, and a 0 (missing client timestamp) must not become
        the cycle window's start or every later real sample would look
        millions of seconds "slow".
        """
        if now <= 0:
            return []
        completed: list[RepFormRecord] = []
        if not self._buffer.started:
            self._buffer.start = now
            self._buffer.started = True
        if signal is not None:
            self._buffer.samples.append(float(signal))
        if rep_count > self._last_rep:
            cycle_seconds = max(0.0, now - self._buffer.start)
            new_rep = self._last_rep + 1
            signal_min, signal_max = (min(self._buffer.samples), max(self._buffer.samples)) if len(self._buffer.samples) >= 2 else (None, None)
            record = RepFormRecord(
                rep_number=new_rep,
                cycle_seconds=round(cycle_seconds, 2),
                signal_min=None if signal_min is None else round(signal_min, 3),
                signal_max=None if signal_max is None else round(signal_max, 3),
                pace=_pace_verdict(cycle_seconds, self.exercise_id),
                angle=_angle_verdict(signal_min, signal_max, self.exercise_id),
            )
            self.records.append(record)
            completed.append(record)
            self._last_rep = rep_count
            self._buffer = _CycleBuffer(start=now, started=True)
        return completed

    def session_summary(self) -> dict:
        """Aggregate form/pace summary, suitable for ExerciseSession.metrics."""
        if not self.records:
            return {"reps_assessed": 0, "pace": "unknown", "angle": "unknown",
                    "pace_distribution": {}, "angle_distribution": {},
                    "recent_reps": [], "form_ok_reps": 0}
        pace_counts: dict[str, int] = {}
        angle_counts: dict[str, int] = {}
        for record in self.records:
            pace_counts[record.pace] = pace_counts.get(record.pace, 0) + 1
            angle_counts[record.angle] = angle_counts.get(record.angle, 0) + 1
        # Dominant verdict wins the session-level label.
        pace = max(pace_counts, key=lambda key: pace_counts[key])
        angle = max(angle_counts, key=lambda key: angle_counts[key])
        form_ok = sum(1 for record in self.records if record.pace == "ok" and record.angle == "ok")
        recent = [self._record_payload(record) for record in self.records[-10:]]
        return {
            "reps_assessed": len(self.records),
            "pace": pace,
            "pace_label": PACE_LABELS[pace],
            "angle": angle,
            "angle_label": ANGLE_LABELS[angle],
            "pace_distribution": pace_counts,
            "angle_distribution": angle_counts,
            "form_ok_reps": form_ok,
            "recent_reps": recent,
        }

    @staticmethod
    def _record_payload(record: RepFormRecord) -> dict:
        return {"rep": record.rep_number, "cycle_seconds": record.cycle_seconds,
                "signal_min": record.signal_min, "signal_max": record.signal_max,
                "pace": record.pace, "angle": record.angle}
