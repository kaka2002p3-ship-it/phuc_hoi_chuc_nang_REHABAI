"""
Prediction smoothing for real-time inference.

Provides temporal smoothing and confidence-aware voting for stable predictions.
"""

from __future__ import annotations

import numpy as np
from collections import deque
from typing import Optional
from dataclasses import dataclass


@dataclass
class PredictionState:
    """State of a single prediction."""
    exercise_id: int
    confidence: float
    timestamp: float = 0.0


class TemporalSmoother:
    """
    Smooth predictions over a temporal window using exponential moving average.

    Uses confidence-weighted averaging for stable output.
    """

    def __init__(
        self,
        window_size: int = 5,
        alpha: float = 0.6,
        min_confidence: float = 0.4,
    ):
        """
        Args:
            window_size: Number of recent predictions to consider
            alpha: Smoothing factor (0 = all weight to history, 1 = all weight to new)
            min_confidence: Minimum confidence to trust the prediction
        """
        self.window_size = window_size
        self.alpha = alpha
        self.min_confidence = min_confidence
        self.history: deque[PredictionState] = deque(maxlen=window_size)
        self.smoothed_probs = None

    def update(
        self,
        exercise_id: int,
        confidence: float,
        probabilities: Optional[list[float]] = None,
        timestamp: Optional[float] = None,
    ) -> dict:
        """
        Update with new prediction and get smoothed result.

        Args:
            exercise_id: Predicted exercise class
            confidence: Model confidence
            probabilities: Class probabilities (optional)
            timestamp: Prediction timestamp

        Returns:
            Dictionary with smoothed prediction
        """
        if timestamp is None:
            timestamp = np.random.random()  # Fallback

        # Create new state
        new_state = PredictionState(
            exercise_id=exercise_id,
            confidence=confidence,
        )
        self.history.append(new_state)

        # Update smoothed probabilities
        if probabilities is not None:
            new_probs = np.array(probabilities)
            if self.smoothed_probs is None:
                self.smoothed_probs = new_probs
            else:
                # Exponential moving average
                self.smoothed_probs = (
                    self.alpha * new_probs +
                    (1 - self.alpha) * self.smoothed_probs
                )

        # Get smoothed prediction
        if len(self.history) < 2:
            # Not enough history, return current prediction
            return {
                'exercise_id': exercise_id,
                'confidence': confidence,
                'probabilities': probabilities,
                'smoothed': False,
                'history_size': len(self.history),
            }

        # Weighted voting based on confidence
        weighted_votes = {}
        for i, state in enumerate(self.history):
            weight = (i + 1) / len(self.history)  # Recent = higher weight
            if state.exercise_id not in weighted_votes:
                weighted_votes[state.exercise_id] = 0.0
            weighted_votes[state.exercise_id] += weight * state.confidence

        # Get best candidate
        best_id = max(weighted_votes, key=weighted_votes.get)
        best_confidence = weighted_votes[best_id] / sum(1 for _ in self.history)

        return {
            'exercise_id': int(best_id),
            'confidence': float(best_confidence),
            'probabilities': self.smoothed_probs.tolist() if self.smoothed_probs is not None else probabilities,
            'smoothed': True,
            'history_size': len(self.history),
            'raw_confidence': confidence,
        }

    def reset(self):
        """Reset the smoother state."""
        self.history.clear()
        self.smoothed_probs = None


class ConfidenceAwareVoter:
    """
    Voting system that requires multiple confirmations before accepting a prediction.

    Reduces noise from transient predictions.
    """

    def __init__(
        self,
        confirmations_needed: int = 2,
        min_confidence: float = 0.5,
        confidence_threshold_for_vote: float = 0.4,
        decay_rate: float = 0.8,
    ):
        """
        Args:
            confirmations_needed: Number of consecutive confirmations required
            min_confidence: Minimum confidence to consider a prediction valid
            confidence_threshold_for_vote: Minimum confidence to count as confirmation
            decay_rate: Decay rate for old confirmations
        """
        self.confirmations_needed = confirmations_needed
        self.min_confidence = min_confidence
        self.confidence_threshold_for_vote = confidence_threshold_for_vote
        self.decay_rate = decay_rate

        self.votes: dict[int, float] = {}  # exercise_id -> accumulated confidence
        self.last_prediction: Optional[int] = None
        self.confirmation_count: int = 0

    def vote(
        self,
        exercise_id: int,
        confidence: float,
        probabilities: Optional[list[float]] = None,
    ) -> dict:
        """
        Submit a vote and check if prediction is confirmed.

        Args:
            exercise_id: Predicted exercise class
            confidence: Model confidence

        Returns:
            Dictionary with:
            - confirmed: Whether prediction is confirmed
            - exercise_id: Confirmed or best candidate exercise_id
            - confidence: Confidence score
            - confirmation_count: Number of consecutive confirmations
        """
        # Check confidence threshold
        effective_confidence = max(confidence, self.confidence_threshold_for_vote)

        # Decay old votes
        for vote_id in list(self.votes.keys()):
            self.votes[vote_id] *= self.decay_rate
            if self.votes[vote_id] < 0.1:
                del self.votes[vote_id]

        # Add new vote
        if exercise_id not in self.votes:
            self.votes[exercise_id] = 0.0
        self.votes[exercise_id] += effective_confidence

        # Check for consecutive confirmation
        if exercise_id == self.last_prediction:
            self.confirmation_count += 1
        else:
            self.confirmation_count = 1
            self.last_prediction = exercise_id

        # Get best candidate
        best_id = max(self.votes, key=self.votes.get)
        best_confidence = self.votes[best_id] / sum(self.votes.values())

        # Determine if confirmed
        confirmed = (
            self.confirmation_count >= self.confirmations_needed and
            exercise_id == best_id
        )

        return {
            'confirmed': confirmed,
            'exercise_id': int(best_id),
            'confidence': float(best_confidence),
            'probabilities': probabilities,
            'confirmation_count': self.confirmation_count,
            'is_current_prediction': exercise_id == best_id,
        }

    def reset(self):
        """Reset voting state."""
        self.votes.clear()
        self.last_prediction = None
        self.confirmation_count = 0


class KalmanFilterSmoother:
    """
    Kalman filter for smoothing 1D predictions (class probabilities over time).

    Provides optimal smoothing when measurement noise is known.
    """

    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        initial_state: Optional[np.ndarray] = None,
    ):
        """
        Args:
            process_noise: Expected variance in true state between measurements
            measurement_noise: Expected variance in measurements
            initial_state: Initial state estimate
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.state = initial_state
        self.error_covariance = 1.0
        self.initialized = False

    def update(self, measurement: np.ndarray) -> np.ndarray:
        """
        Update filter with new measurement.

        Args:
            measurement: New observation (class probabilities)

        Returns:
            Smoothed state estimate
        """
        if not self.initialized:
            self.state = measurement.copy()
            self.initialized = True
            return self.state.copy()

        # Prediction step
        predicted_state = self.state.copy()
        predicted_covariance = self.error_covariance + self.process_noise

        # Update step
        kalman_gain = predicted_covariance / (predicted_covariance + self.measurement_noise)
        innovation = measurement - predicted_state

        self.state = predicted_state + kalman_gain * innovation
        self.error_covariance = (1 - kalman_gain) * predicted_covariance

        # Ensure valid probabilities
        self.state = np.clip(self.state, 0, 1)
        self.state = self.state / (self.state.sum() + 1e-8)

        return self.state.copy()

    def reset(self):
        """Reset the filter."""
        self.state = None
        self.error_covariance = 1.0
        self.initialized = False


class EnsemblePredictor:
    """
    Combines multiple smoothing strategies for robust output.

    Uses:
    - Temporal smoothing for stability
    - Confidence voting for confirmation
    - Kalman filtering for probability smoothing
    """

    def __init__(
        self,
        window_size: int = 5,
        confirmations_needed: int = 2,
        min_confidence: float = 0.5,
    ):
        self.temporal_smoother = TemporalSmoother(
            window_size=window_size,
            alpha=0.5,
        )
        self.voter = ConfidenceAwareVoter(
            confirmations_needed=confirmations_needed,
            min_confidence=min_confidence,
        )
        self.kalman = KalmanFilterSmoother(
            measurement_noise=0.3,
        )

    def predict(
        self,
        exercise_id: int,
        confidence: float,
        probabilities: Optional[list[float]] = None,
    ) -> dict:
        """
        Get ensemble-smoothed prediction.

        Args:
            exercise_id: Raw predicted exercise class
            confidence: Raw confidence score
            probabilities: Class probabilities

        Returns:
            Ensemble-smoothed prediction
        """
        # Update Kalman filter with probabilities
        if probabilities is not None:
            self.kalman.update(np.array(probabilities))
            smoothed_probs = self.kalman.state.tolist()
        else:
            smoothed_probs = None

        # Get temporal smoothed result
        temporal_result = self.temporal_smoother.update(
            exercise_id=exercise_id,
            confidence=confidence,
            probabilities=smoothed_probs,
        )

        # Get voting result
        vote_result = self.voter.vote(
            exercise_id=exercise_id,
            confidence=confidence,
            probabilities=smoothed_probs,
        )

        # Combine results
        confirmed = vote_result['confirmed']
        final_exercise_id = vote_result['exercise_id']
        final_confidence = (
            temporal_result['confidence'] * 0.5 +
            vote_result['confidence'] * 0.5
        )

        return {
            'confirmed': confirmed,
            'exercise_id': final_exercise_id,
            'confidence': final_confidence,
            'probabilities': smoothed_probs,
            'temporal_smoothed': temporal_result['smoothed'],
            'vote_confirmations': vote_result['confirmation_count'],
            'ready_for_use': (
                confirmed and
                temporal_result['history_size'] >= 2
            ),
        }

    def reset(self):
        """Reset all smoothing state."""
        self.temporal_smoother.reset()
        self.voter.reset()
        self.kalman.reset()
