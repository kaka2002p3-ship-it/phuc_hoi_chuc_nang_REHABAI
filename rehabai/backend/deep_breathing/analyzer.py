from __future__ import annotations

from dataclasses import dataclass

from .config import DeepBreathingConfig
from .signal import MotionSignalProcessor
from .state_machine import BreathingStateMachine
from .types import BreathPhase, PoseFrame, SignalQuality, TrackingQuality


@dataclass
class BreathingUpdate:
    phase: BreathPhase
    cycle_index: int
    completed_cycles: int
    interrupted_cycles: int
    tracking_quality: TrackingQuality
    signal_quality: SignalQuality
    elapsed_seconds: float
    event: str | None = None
    confidence: str = "UNKNOWN"


class BreathingAnalyzer:
    """Timer-guided phase engine with conservative landmark observations."""

    def __init__(self, config: DeepBreathingConfig):
        self.config = config
        self.signal = MotionSignalProcessor(config)
        self.machine = BreathingStateMachine(config)
        self.calibration_frames: list[PoseFrame] = []
        self.calibration_started_at: float | None = None
        self.started_at: float | None = None
        self.completed_cycles = 0
        self.interrupted_cycles = 0
        self._cycle_had_tracking = False
        self._cycle_interrupted = False
        self._cycle_frames = 0
        self._cycle_good_frames = 0
        self._cycle_observed_inhale = False
        self._cycle_observed_exhale = False
        self._last_closed_cycle = 0
        self._last_count_at: float | None = None
        self._last_elapsed = 0.0
        self._observation_candidate = BreathPhase.UNKNOWN
        self._observation_frames = 0

    @property
    def calibrated(self) -> bool:
        return self.signal.calibrated

    def _timer_phase(self, elapsed: float) -> tuple[BreathPhase, int]:
        cycle_seconds = self.config.cycle_seconds
        cycle_index = min(int(elapsed // cycle_seconds) + 1, self.config.target_cycles)
        within = elapsed % cycle_seconds
        if within < self.config.inhale_seconds:
            return BreathPhase.INHALE, cycle_index
        within -= self.config.inhale_seconds
        if self.config.hold_seconds and within < self.config.hold_seconds:
            return BreathPhase.HOLD, cycle_index
        within -= self.config.hold_seconds
        if within < self.config.exhale_seconds:
            return BreathPhase.EXHALE, cycle_index
        return BreathPhase.REST, cycle_index

    def update(self, frame: PoseFrame, timestamp: float) -> BreathingUpdate:
        if self.started_at is None:
            self.started_at = timestamp
            self.calibration_started_at = timestamp
        elapsed = max(0.0, timestamp - self.started_at)

        if not self.calibrated:
            self.calibration_frames.append(frame)
            if elapsed >= self.config.calibration_seconds:
                if not self.signal.calibrate(self.calibration_frames):
                    self.machine.transition(BreathPhase.TRACKING_INSUFFICIENT)
                    return BreathingUpdate(BreathPhase.TRACKING_INSUFFICIENT, 0, 0, 0, TrackingQuality.POOR, SignalQuality.UNKNOWN, elapsed)
                # Guided timing starts only after calibration is accepted.
                self.started_at = timestamp
                elapsed = 0.0
            else:
                return BreathingUpdate(BreathPhase.READY, 0, 0, 0, TrackingQuality.POOR, SignalQuality.UNKNOWN, elapsed)

        sample = self.signal.update(frame)
        timer_phase, cycle_index = self._timer_phase(elapsed)
        if sample.valid:
            self._cycle_had_tracking = True
        self._cycle_frames += 1
        if sample.valid and not sample.artifact_detected:
            self._cycle_good_frames += 1
        if sample.missing_frames >= self.config.long_gap_frames:
            newly_insufficient = self.machine.phase != BreathPhase.TRACKING_INSUFFICIENT
            if self._cycle_had_tracking and not self._cycle_interrupted:
                self.interrupted_cycles += 1
                self._cycle_interrupted = True
            self.machine.transition(BreathPhase.TRACKING_INSUFFICIENT)
            self._last_elapsed = elapsed
            return BreathingUpdate(BreathPhase.TRACKING_INSUFFICIENT, cycle_index, self.completed_cycles, self.interrupted_cycles, sample.tracking_quality, sample.signal_quality, elapsed, "tracking_insufficient" if newly_insufficient else None, "UNKNOWN")

        # Re-enter the guided phase only after tracking becomes usable.
        if self.machine.phase == BreathPhase.IDLE:
            self.machine.transition(BreathPhase.READY)
        if self.machine.phase == BreathPhase.TRACKING_INSUFFICIENT:
            self.machine.transition(BreathPhase.READY)
        if self.machine.phase in {BreathPhase.READY, BreathPhase.UNKNOWN}:
            self.machine.transition(timer_phase)
        elif self.machine.phase != timer_phase:
            # A cycle boundary is closed through READY; this prevents the
            # invalid EXHALE -> INHALE jump and makes duplicate counting safe.
            if self.machine.phase == BreathPhase.EXHALE and timer_phase == BreathPhase.INHALE:
                self.machine.transition(BreathPhase.READY)
            self.machine.transition(timer_phase)

        event = None
        previous_cycle = int(self._last_elapsed // self.config.cycle_seconds)
        current_cycle = int(elapsed // self.config.cycle_seconds)
        just_finished = current_cycle > previous_cycle
        if just_finished and current_cycle > self._last_closed_cycle:
            good_ratio = self._cycle_good_frames / max(self._cycle_frames, 1)
            duration_valid = self.config.min_cycle_seconds <= self.config.cycle_seconds <= self.config.max_cycle_seconds
            if (self._cycle_had_tracking and not self._cycle_interrupted
                    and self._cycle_observed_inhale and self._cycle_observed_exhale
                    and good_ratio >= self.config.min_good_frames_ratio and duration_valid):
                if self._last_count_at is None or elapsed - self._last_count_at >= self.config.count_cooldown_seconds:
                    self.completed_cycles = min(self.completed_cycles + 1, self.config.target_cycles)
                    self._last_count_at = elapsed
                    event = "cycle_completed"
            else:
                if not self._cycle_interrupted:
                    self.interrupted_cycles += 1
                self._cycle_interrupted = True
                event = "cycle_interrupted"
            self._last_closed_cycle = current_cycle
            self._cycle_had_tracking = False
            self._cycle_interrupted = False
            self._cycle_frames = 0
            self._cycle_good_frames = 0
            self._cycle_observed_inhale = False
            self._cycle_observed_exhale = False
        if self.completed_cycles >= self.config.target_cycles:
            self.machine.transition(BreathPhase.COMPLETED)
        observed = BreathPhase.UNKNOWN
        if sample.valid and not sample.artifact_detected and sample.velocity is not None:
            if sample.velocity >= self.config.rise_threshold:
                observed = BreathPhase.INHALE
            elif sample.velocity <= self.config.fall_threshold:
                observed = BreathPhase.EXHALE
            elif abs(sample.velocity) <= self.config.neutral_threshold:
                observed = BreathPhase.HOLD
        if observed == self._observation_candidate:
            self._observation_frames += 1
        else:
            self._observation_candidate = observed
            self._observation_frames = 1
        stable_observation = self._observation_frames >= self.config.min_phase_frames
        aligned = stable_observation and (
            observed == timer_phase or (timer_phase == BreathPhase.REST and observed == BreathPhase.HOLD)
        )
        if aligned and timer_phase == BreathPhase.INHALE:
            self._cycle_observed_inhale = True
        elif aligned and timer_phase == BreathPhase.EXHALE:
            self._cycle_observed_exhale = True
        confidence = "HIGH" if aligned and sample.tracking_quality == TrackingQuality.GOOD else "MEDIUM" if sample.valid and stable_observation else "LOW" if sample.valid else "UNKNOWN"
        self._last_elapsed = elapsed
        return BreathingUpdate(self.machine.phase, cycle_index, self.completed_cycles, self.interrupted_cycles, sample.tracking_quality if sample.valid else TrackingQuality.POOR, sample.signal_quality, elapsed, event, confidence)

    def timer_only_update(self, elapsed: float) -> BreathingUpdate:
        phase, cycle_index = self._timer_phase(max(0.0, elapsed))
        completed = min(int(max(0.0, elapsed) // self.config.cycle_seconds), self.config.target_cycles)
        event = "cycle_completed" if completed > self.completed_cycles else None
        self.completed_cycles = completed
        self.machine.phase = BreathPhase.COMPLETED if completed >= self.config.target_cycles else phase
        return BreathingUpdate(self.machine.phase, cycle_index, completed, 0, TrackingQuality.UNAVAILABLE, SignalQuality.UNKNOWN, elapsed, event, "UNKNOWN")

    def finish(self, status: str = "COMPLETED") -> dict:
        return {
            "completed_cycles": self.completed_cycles,
            "interrupted_cycles": self.interrupted_cycles,
            "tracking_quality": TrackingQuality.GOOD.value if self.calibrated else TrackingQuality.UNAVAILABLE.value,
            "status": status,
        }
