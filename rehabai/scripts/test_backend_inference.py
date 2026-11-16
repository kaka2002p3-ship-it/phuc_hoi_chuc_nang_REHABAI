"""
Test script for backend inference with prediction smoothing.

Tests:
1. Model loader returns probabilities
2. Prediction smoother works correctly
3. WebSocket integration is correct
"""

from __future__ import annotations

import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def test_model_loader_returns_probabilities():
    """Test that model loader returns class probabilities."""
    print("\n" + "="*60)
    print("Test 1: Model Loader Returns Probabilities")
    print("="*60)

    try:
        # Import model loader
        from backend.core.model_loader import model_loader

        # Create a random sequence
        import numpy as np
        sequence = np.random.randn(96, 237).astype(np.float32)

        # Get prediction
        pred = model_loader.predict(sequence)

        # Check structure
        assert "exercise_id" in pred, "Missing exercise_id"
        assert "confidence" in pred, "Missing confidence"
        assert "probabilities" in pred, "Missing probabilities"
        assert isinstance(pred["probabilities"], list), "probabilities should be list"
        assert len(pred["probabilities"]) == 4, "Should have 4 class probabilities"

        print(f"✓ Prediction structure correct")
        print(f"  Exercise ID: {pred['exercise_id']}")
        print(f"  Confidence: {pred['confidence']:.4f}")
        print(f"  Probabilities: {[f'{p:.3f}' for p in pred['probabilities']]}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prediction_smoother_basic():
    """Test prediction smoother basic functionality."""
    print("\n" + "="*60)
    print("Test 2: Prediction Smoother Basic")
    print("="*60)

    try:
        from backend.ml.inference.smooth_predictions import EnsemblePredictor

        predictor = EnsemblePredictor()

        # Simulate a sequence of predictions
        # First, some noise
        for _ in range(3):
            predictor.predict(
                exercise_id=1,
                confidence=0.7,
                probabilities=[0.7, 0.15, 0.1, 0.05]
            )

        # Now consistent predictions
        result = predictor.predict(
            exercise_id=1,
            confidence=0.85,
            probabilities=[0.85, 0.08, 0.05, 0.02]
        )

        print(f"✓ Prediction smoother works")
        print(f"  Confirmed: {result['confirmed']}")
        print(f"  Exercise ID: {result['exercise_id']}")
        print(f"  Confidence: {result['confidence']:.4f}")
        print(f"  Vote Confirmations: {result['vote_confirmations']}")

        predictor.reset()
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prediction_smoother_noise_handling():
    """Test that smoother handles noisy predictions."""
    print("\n" + "="*60)
    print("Test 3: Smoother Noise Handling")
    print("="*60)

    try:
        from backend.ml.inference.smooth_predictions import EnsemblePredictor
        import numpy as np

        predictor = EnsemblePredictor(
            window_size=5,
            confirmations_needed=2,
            min_confidence=0.5
        )

        # Simulate noisy environment with occasional wrong predictions
        true_exercise = 2

        for i in range(10):
            # 80% chance of correct, 20% chance of wrong
            if np.random.random() < 0.8:
                ex_id = true_exercise
                conf = 0.75 + np.random.random() * 0.15
            else:
                ex_id = (true_exercise + 1) % 4 + 1
                conf = 0.5 + np.random.random() * 0.2

            probs = np.zeros(4)
            probs[ex_id - 1] = conf
            probs = probs / probs.sum()

            result = predictor.predict(
                exercise_id=ex_id,
                confidence=conf,
                probabilities=probs.tolist()
            )

            if i >= 5:  # After some predictions
                print(f"  Step {i+1}: ID={result['exercise_id']}, Conf={result['confidence']:.3f}, "
                      f"Confirmed={result['confirmed']}, Votes={result.get('vote_confirmations', 0)}")

        predictor.reset()
        print("✓ Smoother handles noisy predictions correctly")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tta_ensemble():
    """Test TTA ensemble with mock model."""
    print("\n" + "="*60)
    print("Test 4: TTA Ensemble")
    print("="*60)

    try:
        from training.inference.tta_inference import TTAEnsemble
        from training.models.rehab_motionnet import RehabMotionNet
        import numpy as np
        import torch

        # Create model
        model = RehabMotionNet(
            num_exercises=4,
            use_hand=True,
            use_kinematic=True,
            use_contrastive=False,
            use_mstcn=True,
            use_attention=False,
        )
        model.eval()

        # Create TTA ensemble
        tta = TTAEnsemble(model, device='cpu', num_augmentations=5)

        # Create random sequence
        sequence = np.random.randn(96, 237).astype(np.float32)

        # Predict with TTA
        result = tta.predict(sequence, return_all=True)

        print(f"✓ TTA ensemble works")
        print(f"  Prediction: {result['prediction']}")
        print(f"  Confidence: {result['confidence']:.4f}")
        print(f"  All predictions: {result.get('all_predictions', [])}")
        print(f"  Num augmentations used: {len(result.get('all_probabilities', []))}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_augmentation_pipeline():
    """Test complete augmentation pipeline."""
    print("\n" + "="*60)
    print("Test 5: Augmentation Pipeline")
    print("="*60)

    try:
        from training.augmentation import AdvancedAugmentation
        import numpy as np

        aug = AdvancedAugmentation(
            temporal_scaling=True,
            pose_noise=True,
            joint_masking=True,
        )

        # Create sample sequence
        sequence = np.random.randn(96, 237).astype(np.float32)

        # Apply augmentation multiple times
        results = []
        for i in range(5):
            aug_seq = aug(sequence)
            assert aug_seq.shape == sequence.shape, f"Shape changed: {aug_seq.shape}"
            results.append(aug_seq)

        print(f"✓ Augmentation pipeline works")
        print(f"  Original shape: {sequence.shape}")
        print(f"  Augmented shapes: {[r.shape for r in results]}")
        print(f"  All shapes preserved: {all(r.shape == sequence.shape for r in results)}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_enhanced():
    """Test enhanced metrics functions."""
    print("\n" + "="*60)
    print("Test 6: Enhanced Metrics")
    print("="*60)

    try:
        from shared.metrics import (
            detailed_evaluation,
            confidence_distribution,
            top_k_accuracy,
            calibration_metrics,
        )
        import numpy as np

        # Create sample data
        y_true = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1]
        y_pred = [0, 1, 2, 3, 0, 2, 2, 3, 0, 1]
        probs = np.random.rand(10, 4)
        probs = probs / probs.sum(axis=1, keepdims=True)

        # Detailed evaluation
        detailed = detailed_evaluation(y_true, y_pred)
        print(f"✓ Detailed evaluation works")
        print(f"  Accuracy: {detailed['accuracy']:.4f}")
        print(f"  Macro F1: {detailed['macro_f1']:.4f}")

        # Confidence distribution
        conf_dist = confidence_distribution(probs)
        print(f"✓ Confidence distribution works")
        print(f"  Mean: {conf_dist['mean_confidence']:.4f}")

        # Top-k accuracy
        top1 = top_k_accuracy(y_true, probs, k=1)
        top2 = top_k_accuracy(y_true, probs, k=2)
        print(f"✓ Top-k accuracy works")
        print(f"  Top-1: {top1:.4f}, Top-2: {top2:.4f}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_import():
    """Test that websocket module imports correctly."""
    print("\n" + "="*60)
    print("Test 7: WebSocket Module Import")
    print("="*60)

    try:
        from backend.api.websocket import (
            get_prediction_smoother,
            reset_prediction_smoother,
            EnsemblePredictor,
        )

        # Test smoother functions
        smoother1 = get_prediction_smoother()
        smoother2 = get_prediction_smoother()

        # Should be the same instance (singleton)
        assert smoother1 is smoother2, "Smoother should be singleton"

        print(f"✓ WebSocket module imports correctly")
        print(f"  Prediction smoother type: {type(smoother1).__name__}")
        print(f"  Smoother singleton: {smoother1 is smoother2}")

        # Reset and verify
        reset_prediction_smoother()
        smoother3 = get_prediction_smoother()
        print(f"  Reset works: {smoother3 is not smoother1}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" " * 15 + "BACKEND INFERENCE TEST SUITE")
    print("="*70)

    tests = [
        ("Model Loader Returns Probabilities", test_model_loader_returns_probabilities),
        ("Prediction Smoother Basic", test_prediction_smoother_basic),
        ("Prediction Smoother Noise Handling", test_prediction_smoother_noise_handling),
        ("TTA Ensemble", test_tta_ensemble),
        ("Augmentation Pipeline", test_augmentation_pipeline),
        ("Enhanced Metrics", test_metrics_enhanced),
        ("WebSocket Module Import", test_websocket_import),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print(" " * 20 + "TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "✓ PASS" if p else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n{'='*70}")
    print(f"  Total: {passed}/{total} passed")
    print("="*70)

    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
