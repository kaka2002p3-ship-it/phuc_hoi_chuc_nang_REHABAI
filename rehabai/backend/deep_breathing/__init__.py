"""Rule-based guided breathing engine.

This package deliberately contains no trainable model.  It turns optional pose
landmarks into conservative motion observations and guided-timer events.
"""

from .config import DeepBreathingConfig
from .types import BreathPhase, TrackingQuality, SignalQuality

__all__ = ["DeepBreathingConfig", "BreathPhase", "TrackingQuality", "SignalQuality"]
