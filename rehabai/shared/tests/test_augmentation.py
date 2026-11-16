"""Tests for augmentation functions."""
import numpy as np
from shared.preprocessing.augmentation import (
    add_gaussian_noise,
    random_rotation_y,
    random_landmark_masking,
    mixup_sequences,
    temporal_jitter,
    temporal_crop_and_pad,
    random_mask_body_region,
    compose_augmentations,
)


def test_gaussian_noise_shape():
    """Test that gaussian noise preserves shape."""
    landmarks = np.random.randn(96, 33, 3)
    noisy = add_gaussian_noise(landmarks, std=0.01)
    assert noisy.shape == landmarks.shape


def test_gaussian_noise_zero_handling():
    """Test that zero landmarks stay zero."""
    landmarks = np.zeros((10, 5, 3))
    landmarks[0, 0] = [1, 1, 1]
    noisy = add_gaussian_noise(landmarks, std=0.01)
    assert np.all(noisy[1:] == 0)


def test_rotation_shape():
    """Test that rotation preserves shape."""
    landmarks = np.random.randn(96, 33, 3)
    rotated = random_rotation_y(landmarks, max_angle_degrees=10)
    assert rotated.shape == landmarks.shape


def test_rotation_zero_handling():
    """Test that zero landmarks stay zero after rotation."""
    landmarks = np.zeros((10, 5, 3))
    landmarks[:, 0, :] = [0.1, 0.1, 0.1]
    rotated = random_rotation_y(landmarks, max_angle_degrees=10)
    # Check that originally zero joints are still zero
    assert np.allclose(rotated[:, 1:, :], 0)


def test_landmark_masking_shape():
    """Test that masking preserves shape."""
    landmarks = np.random.randn(96, 33, 3)
    masked = random_landmark_masking(landmarks, prob=0.1)
    assert masked.shape == landmarks.shape


def test_mixup_sequences_shape():
    """Test that MixUp preserves shape."""
    seq1 = np.random.randn(96, 237)
    seq2 = np.random.randn(96, 237)
    mixed = mixup_sequences(seq1, seq2, alpha=0.2)
    assert mixed.shape == seq1.shape


def test_mixup_ranges():
    """Test that MixUp output is in valid range."""
    seq1 = np.zeros((10, 10))
    seq1[:, 0] = 1.0
    seq2 = np.zeros((10, 10))
    seq2[:, 0] = 0.0

    # Run multiple times to test stochasticity
    for _ in range(5):
        mixed = mixup_sequences(seq1, seq2, alpha=0.2)
        assert mixed.shape == seq1.shape
        # Values should be between 0 and 1
        assert mixed[:, 0].min() >= 0
        assert mixed[:, 0].max() <= 1


def test_mixup_different_shapes_error():
    """Test that MixUp raises error on shape mismatch."""
    seq1 = np.random.randn(96, 237)
    seq2 = np.random.randn(96, 100)
    try:
        mixup_sequences(seq1, seq2)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_temporal_jitter_shape():
    """Test that temporal jitter preserves shape."""
    sequence = np.random.randn(96, 237)
    jittered = temporal_jitter(sequence, noise_std=0.02)
    assert jittered.shape == sequence.shape


def test_temporal_jitter_zero_handling():
    """Test that zero frames stay zero."""
    sequence = np.zeros((10, 5))
    sequence[0, 0] = 1.0
    jittered = temporal_jitter(sequence, noise_std=0.01)
    # First frame should be non-zero (has the signal)
    # But zero frames should not get noise added
    assert np.abs(jittered[1:]).sum() < 0.1


def test_temporal_crop_pad_shape():
    """Test that crop and pad returns original length."""
    sequence = np.random.randn(96, 237)
    cropped = temporal_crop_and_pad(sequence, crop_ratio=0.1)
    assert cropped.shape == sequence.shape


def test_temporal_crop_pad_deterministic():
    """Test with zero crop ratio."""
    sequence = np.random.randn(96, 237)
    cropped = temporal_crop_and_pad(sequence, crop_ratio=0.0)
    assert np.allclose(cropped, sequence)


def test_mask_body_region_shapes():
    """Test body region masking preserves shape."""
    for shape in [(96, 33, 3), (96, 17, 3), (96, 63, 3)]:
        landmarks = np.random.randn(*shape)
        masked = random_mask_body_region(landmarks, prob=0.1)
        assert masked.shape == landmarks.shape


def test_mask_body_region_all_zeros():
    """Test that all-zero landmarks stay all-zero."""
    landmarks = np.zeros((10, 17, 3))
    masked = random_mask_body_region(landmarks, prob=0.5)
    assert np.allclose(masked, 0)


def test_mask_body_region_regions():
    """Test specific body regions."""
    landmarks = np.random.randn(10, 17, 3)

    # Test each region doesn't crash
    for region in ['left_arm', 'right_arm', 'left_hand', 'right_hand']:
        masked = random_mask_body_region(landmarks, prob=0.1, region=region)
        assert masked.shape == landmarks.shape


def test_compose_augmentations_shape():
    """Test that compose_augmentations preserves shape."""
    sequence = np.random.randn(96, 237)
    augmented = compose_augmentations(sequence)
    assert augmented.shape == sequence.shape


def test_compose_augmentations_no_ops():
    """Test with all augmentations disabled."""
    sequence = np.random.randn(96, 237)
    augmented = compose_augmentations(
        sequence,
        enable_gaussian=False,
        enable_rotation=False,
        enable_masking=False,
        enable_mixup=False,
    )
    assert augmented.shape == sequence.shape


def test_compose_augmentations_with_mixup():
    """Test compose with MixUp partner."""
    sequence = np.random.randn(96, 237)
    partner = np.random.randn(96, 237)
    augmented = compose_augmentations(
        sequence,
        enable_mixup=True,
        mixup_partner=partner,
        augmentation_prob=1.0,
    )
    assert augmented.shape == sequence.shape


if __name__ == "__main__":
    print("Running augmentation tests...")

    test_gaussian_noise_shape()
    print("✓ Gaussian noise shape")

    test_gaussian_noise_zero_handling()
    print("✓ Gaussian noise zero handling")

    test_rotation_shape()
    print("✓ Rotation shape")

    test_rotation_zero_handling()
    print("✓ Rotation zero handling")

    test_landmark_masking_shape()
    print("✓ Landmark masking shape")

    test_mixup_sequences_shape()
    print("✓ MixUp shape")

    test_mixup_ranges()
    print("✓ MixUp ranges")

    test_mixup_different_shapes_error()
    print("✓ MixUp error on shape mismatch")

    test_temporal_jitter_shape()
    print("✓ Temporal jitter shape")

    test_temporal_jitter_zero_handling()
    print("✓ Temporal jitter zero handling")

    test_temporal_crop_pad_shape()
    print("✓ Temporal crop/pad shape")

    test_temporal_crop_pad_deterministic()
    print("✓ Temporal crop/pad deterministic")

    test_mask_body_region_shapes()
    print("✓ Body region masking shapes")

    test_mask_body_region_all_zeros()
    print("✓ Body region masking all zeros")

    test_mask_body_region_regions()
    print("✓ Body region regions")

    test_compose_augmentations_shape()
    print("✓ Compose augmentations shape")

    test_compose_augmentations_no_ops()
    print("✓ Compose augmentations no ops")

    test_compose_augmentations_with_mixup()
    print("✓ Compose augmentations with MixUp")

    print("\n✅ All augmentation tests passed!")
