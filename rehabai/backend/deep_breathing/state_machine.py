from __future__ import annotations

from .config import DeepBreathingConfig
from .types import BreathPhase


VALID_TRANSITIONS: dict[BreathPhase, set[BreathPhase]] = {
    BreathPhase.IDLE: {BreathPhase.READY, BreathPhase.PAUSED},
    BreathPhase.READY: {BreathPhase.INHALE, BreathPhase.PAUSED, BreathPhase.TRACKING_INSUFFICIENT},
    BreathPhase.INHALE: {BreathPhase.HOLD, BreathPhase.EXHALE, BreathPhase.COMPLETED, BreathPhase.UNKNOWN, BreathPhase.TRACKING_INSUFFICIENT, BreathPhase.PAUSED},
    BreathPhase.HOLD: {BreathPhase.EXHALE, BreathPhase.UNKNOWN, BreathPhase.TRACKING_INSUFFICIENT, BreathPhase.PAUSED},
    BreathPhase.EXHALE: {BreathPhase.REST, BreathPhase.READY, BreathPhase.COMPLETED, BreathPhase.UNKNOWN, BreathPhase.TRACKING_INSUFFICIENT, BreathPhase.PAUSED},
    BreathPhase.REST: {BreathPhase.READY, BreathPhase.INHALE, BreathPhase.COMPLETED, BreathPhase.PAUSED},
    BreathPhase.UNKNOWN: {BreathPhase.READY, BreathPhase.INHALE, BreathPhase.TRACKING_INSUFFICIENT, BreathPhase.PAUSED},
    BreathPhase.TRACKING_INSUFFICIENT: {BreathPhase.READY, BreathPhase.UNKNOWN, BreathPhase.PAUSED},
    BreathPhase.PAUSED: {BreathPhase.READY, BreathPhase.INHALE, BreathPhase.COMPLETED},
    BreathPhase.COMPLETED: set(),
}


class BreathingStateMachine:
    def __init__(self, config: DeepBreathingConfig):
        self.config = config
        self.phase = BreathPhase.IDLE
        self.transitions: list[tuple[BreathPhase, BreathPhase]] = []

    def transition(self, next_phase: BreathPhase) -> bool:
        if next_phase == self.phase:
            return True
        if next_phase not in VALID_TRANSITIONS.get(self.phase, set()):
            return False
        previous = self.phase
        self.phase = next_phase
        self.transitions.append((previous, next_phase))
        return True

    def reset(self) -> None:
        self.phase = BreathPhase.IDLE
        self.transitions.clear()
