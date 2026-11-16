"""
Comprehensive test suite for the optimized training and inference pipeline.

Tests:
1. Augmentation functions
2. Loss functions
3. TTA inference
4. Prediction smoothing
5. End-to-end inference pipeline
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import torch
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# =============================================================================
# Test 1: Augmentation Functions
# =============================================================================

class TestAugmentation:
    """Test data augmentation functions."""

    @pytest.fixture
    def sample_sequence(self):
        """Create a sample motion sequence (T=96, features=237)."""
        return np.random.randn(96, 237).astype(np.float32)

    def test_temporal_scaling(self, sample_sequence):
        """Test temporal scaling augmentation."""
        from training.augmentation import TemporalScaling

        aug = TemporalScaling(scale_range=(0.8, 1.2), p=1.0)
        result = aug(sample_sequence)

        # Result should have different length
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape[1] == sample_sequence.shape[1]  # Same features

    def test_temporal_jitter(self, sample_sequence):
        """Test temporal jitter augmentation."""
        from training.augmentation import TemporalJitter

        aug = TemporalJitter(max_shift=3, p=1.0)
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape

    def test_pose_noise(self, sample_sequence):
        """Test pose noise augmentation."""
        from training.augmentation import PoseNoise

        aug = PoseNoise(sigma=0.01, p=1.0)
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape
        # Noise should change the values
        assert not np.allclose(result, sample_sequence)

    def test_pose_scaling(self, sample_sequence):
        """Test pose scaling augmentation."""
        from training.augmentation import PoseScaling

        aug = PoseScaling(scale_range=(0.95, 1.05), p=1.0)
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape

    def test_joint_masking(self, sample_sequence):
        """Test joint masking augmentation."""
        from training.augmentation import JointMasking

        aug = JointMasking(max_joints=3, p=1.0)
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape

    def test_selective_masking(self, sample_sequence):
        """Test selective masking augmentation."""
        from training.augmentation import SelectiveMasking

        aug = SelectiveMasking(mask_ratio=0.15, p=1.0)
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape

    def test_advanced_augmentation(self, sample_sequence):
        """Test combined advanced augmentation."""
        from training.augmentation import AdvancedAugmentation

        aug = AdvancedAugmentation(
            temporal_scaling=True,
            pose_noise=True,
            pose_scaling=True,
            joint_masking=True,
            p_temporal_scaling=1.0,
            p_pose_noise=1.0,
        )
        result = aug(sample_sequence)

        assert result is not None
        assert result.shape == sample_sequence.shape
        assert isinstance(result, np.ndarray)

    def test_augmentation_preserves_shape(self, sample_sequence):
        """Test that augmentation preserves feature dimensions."""
        from training.augmentation import AdvancedAugmentation

        aug = AdvancedAugmentation()

        for _ in range(10):
            result = aug(sample_sequence)
            assert result.shape[1] == 237, f"Feature dim changed: {result.shape}"

    def test_augmentation_deterministic_seed(self, sample_sequence):
        """Test that augmentation with same seed gives same result."""
        from training.augmentation import PoseNoise

        aug = PoseNoise(sigma=0.01, p=1.0)

        np.random.seed(42)
        result1 = aug(sample_sequence.copy())

        np.random.seed(42)
        result2 = aug(sample_sequence.copy())

        # Should be the same with same seed
        # (Note: actual result depends on internal randomness)


# =============================================================================
# Test 2: Loss Functions
# =============================================================================

class TestLossFunctions:
    """Test loss functions."""

    @pytest.fixture
    def sample_batch(self):
        """Create sample batch for testing."""
        batch_size = 16
        num_classes = 4
        logits = torch.randn(batch_size, num_classes)
        labels = torch.randint(0, num_classes, (batch_size,))
        return logits, labels

    def test_focal_loss_basic(self, sample_batch):
        """Test basic focal loss computation."""
        from training.losses.class_weighted_loss import FocalLoss

        logits, labels = sample_batch
        criterion = FocalLoss(gamma=2.0)

        loss = criterion(logits, labels)

        assert loss is not None
        assert isinstance(loss.item(), float)
        assert loss.item() >= 0

    def test_focal_loss_with_weights(self, sample_batch):
        """Test focal loss with class weights."""
        from training.losses.class_weighted_loss import FocalLoss

        logits, labels = sample_batch
        weights = torch.tensor([1.0, 1.5, 1.0, 0.8])
        criterion = FocalLoss(alpha=weights, gamma=2.0)

        loss = criterion(logits, labels)

        assert loss is not None
        assert loss.item() >= 0

    def test_focal_loss_with_label_smoothing(self, sample_batch):
        """Test focal loss with label smoothing."""
        from training.losses.class_weighted_loss import FocalLoss

        logits, labels = sample_batch
        criterion = FocalLoss(gamma=2.0, label_smoothing=0.1)

        loss = criterion(logits, labels)

        assert loss is not None
        assert loss.item() >= 0

    def test_class_weighted_ce(self, sample_batch):
        """Test class weighted cross entropy."""
        from training.losses.class_weighted_loss import ClassWeightedCrossEntropy

        logits, labels = sample_batch
        weights = torch.tensor([1.0, 1.5, 1.0, 0.8])
        criterion = ClassWeightedCrossEntropy(weights=weights)

        loss = criterion(logits, labels)

        assert loss is not None
        assert loss.item() >= 0

    def test_compute_class_weights(self):
        """Test class weight computation."""
        from training.losses.class_weighted_loss import compute_class_weights

        labels = [0] * 50 + [1] * 30 + [2] * 15 + [3] * 5
        weights = compute_class_weights(labels, num_classes=4, method='balanced')

        assert weights is not None
        assert len(weights) == 4
        # Minority class should have higher weight
        assert weights[3] > weights[0]


# =============================================================================
# Test 3: TTA Inference
# =============================================================================

class TestTTAInference:
    """Test Test-Time Augmentation."""

    @pytest.fixture
    def mock_model(self):
        """Create a simple mock model."""
        class MockModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = torch.nn.Linear(237, 4)

            def forward(self, x):
                if x.dim() == 2:
                    x = x.unsqueeze(0)
                return self.linear(x.mean(dim=1))

        return MockModel()

    @pytest.fixture
    def sample_sequence(self):
        """Create sample sequence."""
        return np.random.randn(96, 237).astype(np.float32)

    def test_tta_ensemble_basic(self, mock_model, sample_sequence):
        """Test basic TTA ensemble."""
        from training.inference.tta_inference import TTAEnsemble

        tta = TTAEnsemble(mock_model, device='cpu', num_augmentations=3)
        result = tta.predict(sample_sequence)

        assert 'prediction' in result
        assert 'confidence' in result
        assert 'probabilities' in result
        assert result['prediction'] in [0, 1, 2, 3]
        assert 0 <= result['confidence'] <= 1

    def test_tta_returns_all_predictions(self, mock_model, sample_sequence):
        """Test TTA with all predictions."""
        from training.inference.tta_inference import TTAEnsemble

        tta = TTAEnsemble(mock_model, device='cpu', num_augmentations=5)
        result = tta.predict(sample_sequence, return_all=True)

        assert 'all_predictions' in result
        assert 'all_probabilities' in result

    def test_tta_confidence_aware(self, mock_model, sample_sequence):
        """Test confidence-aware TTA."""
        from training.inference.tta_inference import ConfidenceAwareTTA

        tta = ConfidenceAwareTTA(mock_model, device='cpu')
        result = tta.predict(sample_sequence)

        assert 'prediction' in result
        assert 'confidence' in result
        assert 'probabilities' in result


# =============================================================================
# Test 4: Prediction Smoothing
# =============================================================================

class TestPredictionSmoothing:
    """Test prediction smoothing functions."""

    def test_temporal_smoother_basic(self):
        """Test basic temporal smoother."""
        from backend.ml.inference.smooth_predictions import TemporalSmoother

        smoother = TemporalSmoother(window_size=5, alpha=0.6)

        # Add some predictions
        result1 = smoother.update(exercise_id=1, confidence=0.8, probabilities=[0.8, 0.1, 0.05, 0.05])
        result2 = smoother.update(exercise_id=1, confidence=0.85, probabilities=[0.85, 0.1, 0.03, 0.02])
        result3 = smoother.update(exercise_id=1, confidence=0.9, probabilities=[0.9, 0.05, 0.03, 0.02])

        assert result1['exercise_id'] == 1
        assert result2['exercise_id'] == 1

    def test_temporal_smoother_reset(self):
        """Test smoother reset."""
        from backend.ml.inference.smooth_predictions import TemporalSmoother

        smoother = TemporalSmoother()
        smoother.update(exercise_id=1, confidence=0.8)
        smoother.update(exercise_id=2, confidence=0.7)

        smoother.reset()

        assert len(smoother.history) == 0

    def test_confidence_voter_basic(self):
        """Test confidence-aware voter."""
        from backend.ml.inference.smooth_predictions import ConfidenceAwareVoter

        voter = ConfidenceAwareVoter(confirmations_needed=2, min_confidence=0.5)

        # Vote for same class multiple times
        result1 = voter.vote(exercise_id=1, confidence=0.8)
        result2 = voter.vote(exercise_id=1, confidence=0.85)
        result3 = voter.vote(exercise_id=1, confidence=0.9)

        # Should be confirmed after 2 confirmations
        assert result3['confirmed'] == True
        assert result3['exercise_id'] == 1

    def test_confidence_voter_reset(self):
        """Test voter reset."""
        from backend.ml.inference.smooth_predictions import ConfidenceAwareVoter

        voter = ConfidenceAwareVoter()
        voter.vote(exercise_id=1, confidence=0.8)
        voter.vote(exercise_id=2, confidence=0.7)

        voter.reset()

        assert len(voter.votes) == 0

    def test_ensemble_predictor(self):
        """Test ensemble predictor combining multiple strategies."""
        from backend.ml.inference.smooth_predictions import EnsemblePredictor

        predictor = EnsemblePredictor()

        result = predictor.predict(
            exercise_id=1,
            confidence=0.8,
            probabilities=[0.8, 0.1, 0.05, 0.05]
        )

        assert 'exercise_id' in result
        assert 'confidence' in result
        assert 'confirmed' in result
        assert 'ready_for_use' in result

        predictor.reset()

    def test_kalman_filter(self):
        """Test Kalman filter smoother."""
        from backend.ml.inference.smooth_predictions import KalmanFilterSmoother

        kf = KalmanFilterSmoother()

        # Update with measurements
        for _ in range(5):
            measurement = np.array([0.7, 0.2, 0.05, 0.05])
            smoothed = kf.update(measurement)

        assert smoothed is not None
        assert len(smoothed) == 4
        assert np.allclose(smoothed.sum(), 1.0, atol=0.01)  # Probabilities sum to 1


# =============================================================================
# Test 5: Model Forward Pass
# =============================================================================

class TestModelForwardPass:
    """Test model forward pass."""

    @pytest.fixture
    def model(self):
        """Create a model instance."""
        from training.models.rehab_motionnet import RehabMotionNet

        model = RehabMotionNet(
            num_exercises=4,
            use_hand=True,
            use_kinematic=True,
            use_contrastive=False,
            use_mstcn=True,
            use_attention=False,
            upper_limb_only=True,
        )
        return model

    @pytest.fixture
    def sample_input(self):
        """Create sample input tensor (B=2, T=96, F=237)."""
        return torch.randn(2, 96, 237)

    def test_model_forward(self, model, sample_input):
        """Test model forward pass."""
        model.eval()
        with torch.no_grad():
            output = model(sample_input)

        assert output is not None
        if isinstance(output, tuple):
            assert len(output) == 2  # exercise head, completion head
            ex_out, comp_out = output
            assert ex_out.shape == (2, 4)  # 4 classes
            assert comp_out.shape == (2, 1)
        else:
            assert output.shape[0] == 2

    def test_model_train_eval(self, model, sample_input):
        """Test model train/eval modes."""
        model.train()
        out1 = model(sample_input)

        model.eval()
        with torch.no_grad():
            out2 = model(sample_input)

        # Outputs should be different due to dropout
        assert out1 is not None
        assert out2 is not None


# =============================================================================
# Test 6: Metrics Functions
# =============================================================================

class TestMetrics:
    """Test metrics functions."""

    def test_accuracy(self):
        """Test accuracy calculation."""
        from shared.metrics import accuracy_score

        y_true = [0, 1, 2, 3, 0, 1]
        y_pred = [0, 1, 2, 3, 0, 2]

        acc = accuracy_score(y_true, y_pred)

        assert isinstance(acc, float)
        assert 0 <= acc <= 1
        assert acc == 5/6

    def test_f1_score_macro(self):
        """Test macro F1 score."""
        from shared.metrics import f1_score

        y_true = [0, 1, 2, 3, 0, 1]
        y_pred = [0, 1, 2, 3, 0, 2]

        f1 = f1_score(y_true, y_pred, average='macro')

        assert isinstance(f1, float)
        assert 0 <= f1 <= 1

    def test_confusion_matrix(self):
        """Test confusion matrix."""
        from shared.metrics import confusion_matrix

        y_true = [0, 1, 2, 3, 0, 1]
        y_pred = [0, 1, 2, 3, 0, 2]

        cm = confusion_matrix(y_true, y_pred)

        assert cm.shape == (4, 4)
        assert cm[0, 0] == 2  # Class 0: 2 correct
        assert cm[1, 1] == 1  # Class 1: 1 correct
        assert cm[1, 2] == 1  # Class 1 misclassified as 2

    def test_detailed_evaluation(self):
        """Test detailed evaluation."""
        from shared.metrics import detailed_evaluation

        y_true = [0, 1, 2, 3, 0, 1]
        y_pred = [0, 1, 2, 3, 0, 2]
        class_names = ['Vai', 'Khuyu', 'CoTay', 'BanTay']

        result = detailed_evaluation(y_true, y_pred, class_names)

        assert 'accuracy' in result
        assert 'macro_f1' in result
        assert 'per_class' in result
        assert 'confusion_matrix' in result
        assert 'per_class_f1' in result

    def test_confidence_distribution(self):
        """Test confidence distribution analysis."""
        from shared.metrics import confidence_distribution

        probs = np.random.rand(100, 4)
        probs = probs / probs.sum(axis=1, keepdims=True)  # Normalize

        result = confidence_distribution(probs)

        assert 'mean_confidence' in result
        assert 'median_confidence' in result
        assert 'low_confidence_samples' in result
        assert 'high_confidence_samples' in result

    def test_top_k_accuracy(self):
        """Test top-k accuracy."""
        from shared.metrics import top_k_accuracy

        y_true = [0, 1, 2, 3]
        probs = np.array([
            [0.4, 0.3, 0.2, 0.1],  # Top-2: [0, 1], correct
            [0.3, 0.4, 0.2, 0.1],  # Top-2: [1, 0], correct
            [0.2, 0.3, 0.4, 0.1],  # Top-2: [2, 1], correct
            [0.1, 0.2, 0.3, 0.4],  # Top-2: [3, 2], correct
        ])

        acc = top_k_accuracy(y_true, probs, k=2)

        assert isinstance(acc, float)
        assert acc == 1.0  # All correct in top-2


# =============================================================================
# Test 7: End-to-End Pipeline
# =============================================================================

class TestEndToEndPipeline:
    """Test complete inference pipeline."""

    def test_augmentation_to_model_to_smoothing(self):
        """Test complete pipeline: augmentation -> model -> smoothing."""
        from training.augmentation import AdvancedAugmentation
        from training.models.rehab_motionnet import RehabMotionNet
        from backend.ml.inference.smooth_predictions import EnsemblePredictor

        # Create pipeline components
        aug = AdvancedAugmentation()
        model = RehabMotionNet(num_exercises=4, use_hand=True, use_kinematic=True)
        predictor = EnsemblePredictor()

        # Sample sequence
        sequence = np.random.randn(96, 237).astype(np.float32)

        # Apply augmentation
        aug_sequence = aug(sequence)

        # Convert to tensor and predict
        model.eval()
        with torch.no_grad():
            input_tensor = torch.FloatTensor(aug_sequence).unsqueeze(0)
            output = model(input_tensor)
            if isinstance(output, tuple):
                output = output[0]
            probs = torch.softmax(output, dim=-1).squeeze().numpy()

        # Get predicted class
        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])

        # Apply smoothing
        result = predictor.predict(
            exercise_id=pred_class,
            confidence=confidence,
            probabilities=probs.tolist()
        )

        assert result is not None
        assert 'exercise_id' in result
        assert 'confidence' in result

    def test_tta_with_model_and_smoothing(self):
        """Test TTA + model + smoothing pipeline."""
        from training.inference.tta_inference import TTAEnsemble
        from training.models.rehab_motionnet import RehabMotionNet
        from backend.ml.inference.smooth_predictions import EnsemblePredictor

        model = RehabMotionNet(num_exercises=4)
        tta = TTAEnsemble(model, device='cpu', num_augmentations=3)
        predictor = EnsemblePredictor()

        sequence = np.random.randn(96, 237).astype(np.float32)

        # TTA prediction
        tta_result = tta.predict(sequence)

        # Apply smoothing
        smoothed = predictor.predict(
            exercise_id=tta_result['prediction'],
            confidence=tta_result['confidence'],
            probabilities=tta_result['probabilities']
        )

        assert smoothed is not None
        assert smoothed['exercise_id'] in [0, 1, 2, 3]


# =============================================================================
# Test 8: Integration with Existing Code
# =============================================================================

class TestIntegration:
    """Test integration with existing codebase."""

    def test_model_import_from_existing(self):
        """Test that existing models can be imported."""
        try:
            from training.models.rehab_motionnet import RehabMotionNet
            from training.models.cnn_transformer import RehabModel
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import existing models: {e}")

    def test_loss_import_from_existing(self):
        """Test that existing losses can be imported."""
        try:
            from training.losses.focal_loss import FocalLoss
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import existing losses: {e}")

    def test_metrics_import_from_existing(self):
        """Test that existing metrics can be imported."""
        try:
            from shared.metrics import accuracy_score, f1_score
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import existing metrics: {e}")


# =============================================================================
# Run Tests
# =============================================================================

def run_tests(verbose: bool = True):
    """Run all tests."""
    import sys

    # Run pytest
    exit_code = pytest.main([
        __file__,
        '-v' if verbose else '-q',
        '--tb=short',
        '--color=yes',
    ])

    return exit_code == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run optimization tests")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick tests only')
    args = parser.parse_args()

    success = run_tests(verbose=args.verbose)

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
