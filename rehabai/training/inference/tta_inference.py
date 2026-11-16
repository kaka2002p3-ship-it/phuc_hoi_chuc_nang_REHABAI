"""
Test-Time Augmentation (TTA) for inference.

Applies multiple augmentations at test time and averages predictions
for more robust results.
"""

from __future__ import annotations

import numpy as np
import torch
from typing import Optional, Callable
import torch.nn.functional as F


class TTAAugmentation:
    """Base class for TTA augmentations."""

    def __init__(self, p: float = 1.0):
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class TTAHorizontalFlip(TTAAugmentation):
    """Horizontal flip for symmetric motions."""

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        # Mirror left/right in the sequence
        # Assumes sequence format: pose(0:99), left_hand(99:162), right_hand(162:225), kin(225:237)
        result = sequence.copy()
        # Mirror x coordinates
        result[:, 0::3] = -result[:, 0::3]  # x coordinates
        # Swap left and right hand
        result = self._swap_hands(result)
        return result

    def _swap_hands(self, seq: np.ndarray) -> np.ndarray:
        """Swap left and right hand features."""
        result = seq.copy()
        left_hand = seq[:, 99:162].copy()
        right_hand = seq[:, 162:225].copy()
        result[:, 99:162] = right_hand
        result[:, 162:225] = left_hand
        return result


class TTANoise(TTAAugmentation):
    """Add small Gaussian noise."""

    def __init__(self, sigma: float = 0.005, p: float = 1.0):
        super().__init__(p)
        self.sigma = sigma

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        noise = np.random.normal(0, self.sigma, sequence.shape)
        return sequence + noise


class TTAScale(TTAAugmentation):
    """Scale the sequence uniformly."""

    def __init__(
        self,
        scale_factors: tuple[float, float] = (0.95, 1.05),
        p: float = 1.0,
    ):
        super().__init__(p)
        self.scale_factors = scale_factors

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        scale = np.random.uniform(*self.scale_factors)
        # Only scale position features (first 198 = 66 joints * 3)
        result = sequence.copy()
        result[:, :198] *= scale
        return result


class TTATemporalReverse(TTAAugmentation):
    """Reverse the temporal sequence."""

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        return sequence[::-1].copy()


class TTATemporalScale(TTAAugmentation):
    """Scale the temporal dimension."""

    def __init__(
        self,
        scale_range: tuple[float, float] = (0.9, 1.1),
        p: float = 1.0,
    ):
        super().__init__(p)
        self.scale_range = scale_range

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        scale = np.random.uniform(*self.scale_range)
        old_len = len(sequence)
        new_len = int(old_len * scale)

        if new_len < 5:
            return sequence

        result = np.zeros((new_len, sequence.shape[1]), dtype=sequence.dtype)
        old_indices = np.arange(old_len)
        new_indices = np.linspace(0, old_len - 1, new_len)

        for i in range(sequence.shape[1]):
            result[:, i] = np.interp(new_indices, old_indices, sequence[:, i])

        # Resample back to original length for consistent processing
        if new_len != old_len:
            result_final = np.zeros((old_len, sequence.shape[1]), dtype=sequence.dtype)
            indices = np.linspace(0, new_len - 1, old_len)
            for i in range(result.shape[1]):
                result_final[:, i] = np.interp(indices, np.arange(new_len), result[:, i])
            return result_final

        return result


class TTAEnsemble:
    """
    Test-Time Augmentation ensemble.

    Applies multiple views to each input and averages predictions.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        device: str = 'cuda',
        num_augmentations: int = 6,
    ):
        """
        Args:
            model: The PyTorch model for inference
            device: Device to run inference on
            num_augmentations: Number of augmentation views to use
        """
        self.model = model
        self.device = device
        self.num_augmentations = num_augmentations

        # Define augmentation pipeline
        self.augmentations = [
            lambda x: x,  # Original (no augmentation)
            TTANoise(sigma=0.005),
            TTAScale(scale_factors=(0.97, 1.03)),
            TTAScale(scale_factors=(0.95, 1.05)),
            TTATemporalScale(scale_range=(0.95, 1.05)),
        ]

    @torch.no_grad()
    def predict(
        self,
        sequence: np.ndarray,
        return_all: bool = False,
    ) -> dict:
        """
        Predict with TTA.

        Args:
            sequence: Input sequence of shape (T, features)
            return_all: If True, return all individual predictions

        Returns:
            Dictionary with:
            - prediction: Final predicted class
            - confidence: Confidence score
            - probabilities: Class probabilities
            - all_predictions: List of individual predictions (if return_all=True)
        """
        self.model.eval()

        all_probs = []

        for aug in self.augmentations[:self.num_augmentations]:
            # Apply augmentation
            aug_sequence = aug(sequence)

            # Convert to tensor
            input_tensor = torch.FloatTensor(aug_sequence).unsqueeze(0).to(self.device)

            # Forward pass
            logits = self.model(input_tensor)

            # If multi-task model, take first output
            if isinstance(logits, tuple):
                logits = logits[0]

            # Get probabilities
            probs = F.softmax(logits.float(), dim=-1)
            all_probs.append(probs.cpu().numpy())

        # Average probabilities
        avg_probs = np.mean(all_probs, axis=0).squeeze()

        # Get final prediction
        pred_class = int(np.argmax(avg_probs))
        confidence = float(avg_probs[pred_class])

        result = {
            'prediction': pred_class,
            'confidence': confidence,
            'probabilities': avg_probs.tolist(),
        }

        if return_all:
            result['all_predictions'] = [
                np.argmax(p, axis=-1).tolist() for p in all_probs
            ]
            result['all_probabilities'] = [p.squeeze().tolist() for p in all_probs]

        return result

    @torch.no_grad()
    def predict_batch(
        self,
        sequences: list[np.ndarray],
    ) -> list[dict]:
        """
        Predict multiple sequences with TTA.

        Args:
            sequences: List of input sequences

        Returns:
            List of prediction dictionaries
        """
        return [self.predict(seq) for seq in sequences]


class ConfidenceAwareTTA:
    """
    TTA with confidence-based weighting.

    Weights augmentations based on their individual confidence scores.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        device: str = 'cuda',
        min_confidence_threshold: float = 0.3,
    ):
        self.model = model
        self.device = device
        self.min_confidence_threshold = min_confidence_threshold

        self.augmentations = [
            ('original', lambda x: x),
            ('noise_low', TTANoise(sigma=0.003)),
            ('noise_med', TTANoise(sigma=0.01)),
            ('scale_down', TTAScale(scale_factors=(0.95, 0.98))),
            ('scale_up', TTAScale(scale_factors=(1.02, 1.05))),
            ('temporal_slow', TTATemporalScale(scale_range=(0.9, 0.95))),
            ('temporal_fast', TTATemporalScale(scale_range=(1.05, 1.1))),
        ]

    @torch.no_grad()
    def predict(self, sequence: np.ndarray) -> dict:
        weighted_probs = np.zeros(4)  # 4 classes
        total_weight = 0.0

        for name, aug in self.augmentations:
            aug_seq = aug(sequence)
            input_tensor = torch.FloatTensor(aug_seq).unsqueeze(0).to(self.device)

            logits = self.model(input_tensor)
            if isinstance(logits, tuple):
                logits = logits[0]

            probs = F.softmax(logits.float(), dim=-1).cpu().numpy().squeeze()
            confidence = float(np.max(probs))

            # Weight by confidence
            weight = max(confidence, self.min_confidence_threshold)
            weighted_probs += weight * probs
            total_weight += weight

        # Normalize
        weighted_probs /= total_weight

        pred_class = int(np.argmax(weighted_probs))

        return {
            'prediction': pred_class,
            'confidence': float(weighted_probs[pred_class]),
            'probabilities': weighted_probs.tolist(),
        }
