"""
Advanced augmentation for 3D motion sequences (T x 237 features).

Designed for upper-limb rehabilitation exercises where:
- Exercise identity must be preserved
- Temporal dynamics matter
- Tracking noise should be realistic
"""

from __future__ import annotations

import numpy as np
from typing import Sequence, Callable, Optional
import torch


class TemporalScaling:
    """
    Stretch or compress the temporal sequence.

    Unlike random cropping, this preserves all frames by interpolating.
    Scale < 1.0 = compress (faster motion)
    Scale > 1.0 = stretch (slower motion)

    Note: Always returns same sequence length as input for model compatibility.
    """

    def __init__(self, scale_range: tuple[float, float] = (0.8, 1.2), p: float = 0.3):
        self.scale_range = scale_range
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        scale = np.random.uniform(*self.scale_range)
        old_len = len(sequence)

        # Create source indices for interpolation
        old_indices = np.arange(old_len)

        # For scaling, we use temporal interpolation then resample back
        if abs(scale - 1.0) < 0.01:
            return sequence.copy()

        # Interpolate to a different length, then back
        new_len = max(10, int(old_len * scale))

        # Create interpolated sequence at new length
        new_indices = np.linspace(0, old_len - 1, new_len)
        temp_result = np.zeros((new_len, sequence.shape[1]), dtype=sequence.dtype)
        for i in range(sequence.shape[1]):
            temp_result[:, i] = np.interp(new_indices, old_indices, sequence[:, i])

        # Resample back to original length
        final_indices = np.linspace(0, new_len - 1, old_len)
        result = np.zeros((old_len, sequence.shape[1]), dtype=sequence.dtype)
        for i in range(temp_result.shape[1]):
            result[:, i] = np.interp(final_indices, np.arange(new_len), temp_result[:, i])

        return result


class TemporalJitter:
    """
    Add small random temporal shifts to frames.
    Simulates frame rate variations.
    """

    def __init__(self, max_shift: int = 3, p: float = 0.2):
        self.max_shift = max_shift
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        result = sequence.copy()
        shift = np.random.randint(-self.max_shift, self.max_shift + 1)

        if shift == 0:
            return result

        if shift > 0:
            # Shift forward: first frames repeat
            result[shift:] = sequence[:-shift]
            result[:shift] = sequence[0]
        else:
            # Shift backward: last frames repeat
            shift = -shift
            result[:-shift] = sequence[shift:]
            result[-shift:] = sequence[-1]

        return result


class TemporalReverse:
    """
    Reverse the temporal sequence.
    Useful for motion that is temporally symmetric.
    """

    def __init__(self, p: float = 0.1):
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        return sequence[::-1].copy()


class PoseNoise:
    """
    Add Gaussian noise to joint coordinates.
    Simulates tracking noise from MediaPipe.
    """

    def __init__(
        self,
        sigma: float = 0.01,
        per_joint: bool = True,
        p: float = 0.4
    ):
        self.sigma = sigma
        self.per_joint = per_joint
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        result = sequence.copy()

        if self.per_joint:
            # Each joint gets its own noise sample
            noise = np.random.normal(0, self.sigma, sequence.shape)
        else:
            # Same noise across all features (smoother)
            noise = np.random.normal(0, self.sigma, sequence.shape)

        return result + noise


class PoseScaling:
    """
    Uniform scaling of pose coordinates.
    Simulates distance variations from camera.
    """

    def __init__(self, scale_range: tuple[float, float] = (0.95, 1.05), p: float = 0.3):
        self.scale_range = scale_range
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        scale = np.random.uniform(*self.scale_range)

        # Only scale position features (x, y, z), not confidence
        # For 237 features: 33 joints * 3 (xyz) + 33 confidence = 99 + 33 = 132 for pose
        # But our sequences are T x 237, so scale first 198 (66 joints * 3) for pose
        # The remaining features are hand + kinematics
        n_pose_features = 198  # 66 joints * 3 coords

        result = sequence.copy()
        result[:, :n_pose_features] *= scale

        return result


class JointMasking:
    """
    Randomly mask out entire joints (set to zero).
    Simulates occlusions or tracking failures.
    """

    def __init__(self, joint_mask_prob: float = 0.1, max_joints: int = 3, p: float = 0.25):
        self.joint_mask_prob = joint_mask_prob
        self.max_joints = max_joints
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        result = sequence.copy()
        n_joints = 33  # MediaPipe pose joints
        n_coords = 3

        num_to_mask = np.random.randint(1, self.max_joints + 1)
        joints_to_mask = np.random.choice(n_joints, num_to_mask, replace=False)

        for joint in joints_to_mask:
            start_idx = joint * n_coords
            end_idx = start_idx + n_coords
            if end_idx <= result.shape[1]:
                result[:, start_idx:end_idx] = 0

        return result


class SelectiveMasking:
    """
    Randomly mask entire frames.
    Similar to MAE-style masking for self-supervised learning.
    """

    def __init__(self, mask_ratio: float = 0.15, p: float = 0.2):
        self.mask_ratio = mask_ratio
        self.p = p

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence

        result = sequence.copy()
        seq_len = len(sequence)

        num_mask = max(1, int(seq_len * self.mask_ratio))
        mask_indices = np.random.choice(seq_len, num_mask, replace=False)

        # Replace masked frames with interpolated values
        for idx in mask_indices:
            # Find nearest non-masked frames
            non_masked = np.setdiff1d(np.arange(seq_len), mask_indices)
            if len(non_masked) == 0:
                continue

            left = non_masked[non_masked < idx]
            right = non_masked[non_masked > idx]

            if len(left) > 0 and len(right) > 0:
                # Linear interpolation
                l_idx, r_idx = left[-1], right[0]
                alpha = (idx - l_idx) / (r_idx - l_idx)
                result[idx] = (1 - alpha) * sequence[l_idx] + alpha * sequence[r_idx]
            elif len(left) > 0:
                result[idx] = sequence[left[-1]]
            elif len(right) > 0:
                result[idx] = sequence[right[0]]

        return result


class ComposeAugmentations:
    """
    Compose multiple augmentations with individual probabilities.
    Augmentations are applied in order.
    """

    def __init__(self, transforms: list[tuple[Callable, float]]):
        """
        Args:
            transforms: List of (augmentation, probability) tuples
        """
        self.transforms = transforms

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        result = sequence.copy()
        for transform, p in self.transforms:
            result = transform(result)
            # Note: individual transform handles its own probability check
        return result


class AdvancedAugmentation:
    """
    Production-ready augmentation combining temporal and pose augmentations.

    This is the recommended augmentation for training.
    All augmentations preserve exercise class identity.
    """

    def __init__(
        self,
        temporal_scaling: bool = True,
        temporal_jitter: bool = True,
        pose_noise: bool = True,
        pose_scaling: bool = True,
        joint_masking: bool = True,
        selective_masking: bool = True,
        temporal_reverse: bool = True,
        # Probabilities
        p_temporal_scaling: float = 0.3,
        p_temporal_jitter: float = 0.2,
        p_pose_noise: float = 0.4,
        p_pose_scaling: float = 0.3,
        p_joint_masking: float = 0.25,
        p_selective_masking: float = 0.2,
        p_temporal_reverse: float = 0.1,
        # Parameters
        scale_range: tuple[float, float] = (0.8, 1.2),
        noise_sigma: float = 0.01,
        mask_ratio: float = 0.15,
    ):
        self.augmentations = []

        if temporal_scaling:
            self.augmentations.append(TemporalScaling(scale_range, p_temporal_scaling))

        if temporal_jitter:
            self.augmentations.append(TemporalJitter(p=p_temporal_jitter))

        if pose_noise:
            self.augmentations.append(PoseNoise(sigma=noise_sigma, p=p_pose_noise))

        if pose_scaling:
            self.augmentations.append(PoseScaling(p=p_pose_scaling))

        if joint_masking:
            self.augmentations.append(JointMasking(p=p_joint_masking))

        if selective_masking:
            self.augmentations.append(SelectiveMasking(mask_ratio=mask_ratio, p=p_selective_masking))

        if temporal_reverse:
            self.augmentations.append(TemporalReverse(p=p_temporal_reverse))

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        """Apply all augmentations to the sequence."""
        result = sequence.copy()
        for aug in self.augmentations:
            result = aug(result)
        return result

    def __repr__(self) -> str:
        return f"AdvancedAugmentation(augs={len(self.augmentations)})"


class LightAugmentation:
    """
    Light augmentation for validation/small datasets.
    Only applies mild augmentations.
    """

    def __init__(self, p: float = 0.5):
        self.p = p
        self.noise = PoseNoise(sigma=0.005, p=0.3)
        self.scaling = PoseScaling(scale_range=(0.97, 1.03), p=0.3)

    def __call__(self, sequence: np.ndarray) -> np.ndarray:
        if np.random.random() > self.p:
            return sequence
        result = sequence.copy()
        result = self.noise(result)
        result = self.scaling(result)
        return result
