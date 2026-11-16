"""Augmentation strategies for rehabilitation motion sequences.

All functions operate on numpy arrays and are designed to be
composed together in a preprocessing pipeline.
"""
from __future__ import annotations

import numpy as np
from typing import Optional, Tuple


def add_gaussian_noise(landmarks: np.ndarray, std: float = 0.01) -> np.ndarray:
    """
    Add random Gaussian noise to the landmarks.
    landmarks: shape (N, V, 3)
    std: standard deviation of the noise.
    """
    noise = np.random.normal(0, std, landmarks.shape)
    # Don't add noise to (0,0,0) which are missing landmarks
    mask = (landmarks == 0)
    noise[mask] = 0
    return landmarks + noise


def random_rotation_y(landmarks: np.ndarray, max_angle_degrees: float = 10.0) -> np.ndarray:
    """
    Apply a random rotation around the Y-axis (yaw) to simulate different camera angles.
    landmarks: shape (N, V, 3) or (N, D) where D is a flattened feature vector
    """
    angle = np.random.uniform(-max_angle_degrees, max_angle_degrees)
    theta = np.radians(angle)

    c, s = np.cos(theta), np.sin(theta)
    # Rotation matrix around Y axis
    R = np.array([
        [c, 0, s],
        [0, 1, 0],
        [-s, 0, c]
    ])

    result = landmarks.copy()

    # Only apply rotation to 3D landmark data (N, V, 3)
    if landmarks.ndim == 3 and landmarks.shape[-1] == 3:
        rotated = np.dot(landmarks, R.T)
        # Keep missing landmarks at 0
        mask = np.all(landmarks == 0, axis=-1, keepdims=True)
        result = np.where(mask, landmarks, rotated)

    return result


def random_landmark_masking(landmarks: np.ndarray, prob: float = 0.05) -> np.ndarray:
    """
    Randomly mask some landmarks by setting them to 0, to make the model robust to occlusion.
    """
    mask = np.random.rand(*landmarks.shape[:-1]) < prob
    masked_landmarks = landmarks.copy()
    masked_landmarks[mask] = 0
    return masked_landmarks


def mixup_sequences(
    seq1: np.ndarray,
    seq2: np.ndarray,
    alpha: float = 0.2
) -> np.ndarray:
    """
    MixUp augmentation for motion sequences.
    Blends two sequences with a random lambda drawn from Beta distribution.

    Args:
        seq1: First sequence, shape (N, D) or (N, V, C)
        seq2: Second sequence, same shape as seq1
        alpha: Beta distribution parameter (higher = more diverse mixing)

    Returns:
        Mixed sequence with same shape as inputs
    """
    if seq1.shape != seq2.shape:
        raise ValueError(f"Sequences must have same shape, got {seq1.shape} and {seq2.shape}")

    lam = np.random.beta(alpha, alpha)
    # Ensure lambda is not too close to extremes to avoid trivial mixing
    lam = max(0.3, min(0.7, lam))

    return lam * seq1 + (1 - lam) * seq2


def temporal_jitter(
    sequence: np.ndarray,
    noise_std: float = 0.02,
    temporal_std: float = 0.001
) -> np.ndarray:
    """
    Add small temporal noise to a sequence.

    Args:
        sequence: Input sequence, shape (N, D)
        noise_std: Standard deviation for value noise
        temporal_std: Standard deviation for temporal jitter (frame shift)

    Returns:
        Noisy sequence with same shape
    """
    # Value noise
    noise = np.random.normal(0, noise_std, sequence.shape)
    # Don't add noise to zero (missing) values
    mask = np.abs(sequence) < 1e-6
    noise[mask] = 0

    result = sequence + noise

    # Optional: very subtle temporal jitter (shift a few frames)
    if temporal_std > 0 and len(sequence) > 5:
        shift = int(np.random.normal(0, temporal_std * len(sequence)))
        shift = np.clip(shift, -2, 2)
        if shift != 0:
            result = np.roll(result, shift, axis=0)

    return result


def temporal_crop_and_pad(
    sequence: np.ndarray,
    crop_ratio: float = 0.1
) -> np.ndarray:
    """
    Randomly crop a temporal window and pad back to original length.
    Simulates partial motion captures.

    Args:
        sequence: Input sequence, shape (N, D)
        crop_ratio: Fraction of frames to crop (0.0 to 0.5)

    Returns:
        Cropped and padded sequence
    """
    N = len(sequence)
    crop_frames = int(N * crop_ratio)

    if crop_frames > 0:
        start_skip = np.random.randint(0, crop_frames + 1)
        end_skip = np.random.randint(0, crop_frames - start_skip + 1)

        cropped = sequence[start_skip:N - end_skip]

        # Pad back to original length
        if start_skip > 0:
            pad_before = np.tile(cropped[0:1], (start_skip, 1))
            cropped = np.concatenate([pad_before, cropped], axis=0)
        if end_skip > 0:
            pad_after = np.tile(cropped[-1:], (end_skip, 1))
            cropped = np.concatenate([cropped, pad_after], axis=0)

        return cropped[:N]

    return sequence


def random_mask_body_region(
    landmarks: np.ndarray,
    prob: float = 0.1,
    region: Optional[str] = None
) -> np.ndarray:
    """
    Mask out a random body region (upper limb, lower limb, or single side).
    More sophisticated than random_landmark_masking.

    Args:
        landmarks: shape (N, V, 3) or (N, V, C)
        prob: Probability of masking each frame's region
        region: One of 'left_arm', 'right_arm', 'upper', 'lower', or None for random

    Returns:
        Masked landmarks
    """
    N, V = landmarks.shape[:2]
    result = landmarks.copy()

    # Define body regions by MediaPipe landmark indices
    regions = {
        'left_arm': [11, 13, 15],      # L_shoulder, L_elbow, L_wrist
        'right_arm': [12, 14, 16],      # R_shoulder, R_elbow, R_wrist
        'left_hand': list(range(37, 58)),  # MediaPipe hand indices
        'right_hand': list(range(61, 82)),
    }

    if region is None:
        region = np.random.choice(list(regions.keys()))

    if region not in regions:
        return result

    joints = [j for j in regions[region] if j < V]

    # Apply mask to selected joints across random frames
    for joint in joints:
        mask_frames = np.random.rand(N) < prob
        result[mask_frames, joint] = 0

    return result


def compose_augmentations(
    sequence: np.ndarray,
    enable_gaussian: bool = True,
    enable_rotation: bool = True,
    enable_masking: bool = True,
    enable_mixup: bool = False,
    mixup_partner: Optional[np.ndarray] = None,
    augmentation_prob: float = 0.5
) -> np.ndarray:
    """
    Compose multiple augmentation strategies with configurable probabilities.

    Args:
        sequence: Input sequence (N, D) or (N, V, 3)
        enable_gaussian: Enable Gaussian noise
        enable_rotation: Enable Y-axis rotation
        enable_masking: Enable landmark masking
        enable_mixup: Enable MixUp (requires mixup_partner)
        mixup_partner: Partner sequence for MixUp
        augmentation_prob: Base probability for each augmentation

    Returns:
        Augmented sequence
    """
    result = sequence.copy()

    if enable_gaussian and np.random.rand() < augmentation_prob:
        result = add_gaussian_noise(result, std=0.01)

    if enable_rotation and np.random.rand() < augmentation_prob:
        result = random_rotation_y(result, max_angle_degrees=10.0)

    if enable_masking and np.random.rand() < augmentation_prob:
        # Use enhanced masking with body regions
        result = random_mask_body_region(result, prob=0.1)

    if enable_mixup and mixup_partner is not None and np.random.rand() < augmentation_prob * 0.5:
        result = mixup_sequences(result, mixup_partner, alpha=0.2)

    return result
