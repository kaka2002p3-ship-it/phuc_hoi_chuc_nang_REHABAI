"""Tests for enhanced evaluation metrics."""
import numpy as np
from shared.metrics import (
    confusion_matrix,
    detailed_evaluation,
    calibration_metrics,
    confidence_distribution,
    top_k_accuracy,
    accuracy_score,
    f1_score,
)


def test_confusion_matrix_shape():
    """Test that confusion matrix has correct shape."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 1, 2, 1, 2]
    cm = confusion_matrix(y_true, y_pred)
    # 3 classes -> 3x3 matrix
    assert cm.shape == (3, 3)


def test_confusion_matrix_values():
    """Test confusion matrix values are correct."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 1, 2, 1, 2]
    cm = confusion_matrix(y_true, y_pred)
    # Row 0 (true=0): predicted [0, 1, 2] -> [1, 0, 1]
    assert cm[0, 0] == 1  # true=0, pred=0
    assert cm[0, 2] == 1  # true=0, pred=2
    # Row 1 (true=1): predicted [1, 1] -> [0, 2, 0]
    assert cm[1, 1] == 2  # true=1, pred=1
    # Row 2 (true=2): predicted [1, 2] -> [0, 1, 1]
    assert cm[2, 2] == 1  # true=2, pred=2


def test_confusion_matrix_single_class():
    """Test confusion matrix with single class."""
    y_true = [0, 0, 0]
    y_pred = [0, 0, 0]
    cm = confusion_matrix(y_true, y_pred)
    assert cm.shape == (1, 1)
    assert cm[0, 0] == 3


def test_detailed_evaluation_basic():
    """Test detailed evaluation returns expected keys."""
    y_true = [0, 1, 2, 3, 0, 1, 2, 3]
    y_pred = [0, 1, 2, 3, 0, 0, 2, 3]
    classes = ['Class_A', 'Class_B', 'Class_C', 'Class_D']

    result = detailed_evaluation(y_true, y_pred, classes)

    assert 'accuracy' in result
    assert 'macro_f1' in result
    assert 'per_class' in result
    assert 'confusion_matrix' in result
    assert 'summary' in result


def test_detailed_evaluation_accuracy():
    """Test detailed evaluation accuracy calculation."""
    y_true = [0, 1, 2, 3]
    y_pred = [0, 1, 2, 3]
    result = detailed_evaluation(y_true, y_pred)
    assert result['accuracy'] == 1.0


def test_detailed_evaluation_zero_accuracy():
    """Test detailed evaluation with zero accuracy."""
    y_true = [0, 1, 2, 3]
    y_pred = [3, 2, 1, 0]
    result = detailed_evaluation(y_true, y_pred)
    assert result['accuracy'] == 0.0


def test_detailed_evaluation_per_class():
    """Test per-class metrics are calculated."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 2, 2, 1, 2]
    classes = ['A', 'B', 'C']

    result = detailed_evaluation(y_true, y_pred, classes)

    # Class A: 2 samples, 1 correct (50% recall), 1 predicted, 1 correct (100% precision)
    assert result['per_class']['A']['precision'] == 1.0
    assert result['per_class']['A']['recall'] == 0.5
    assert result['per_class']['A']['support'] == 2

    # Class B: 2 samples, 2 correct (100% recall), 2 predicted, 2 correct (100% precision)
    assert result['per_class']['B']['precision'] == 1.0
    assert result['per_class']['B']['recall'] == 1.0

    # Class C: 2 samples, 2 correct (100% recall), 3 predicted, 2 correct (66% precision)
    assert result['per_class']['C']['recall'] == 1.0


def test_detailed_evaluation_per_class_f1():
    """Test per-class F1 is accessible."""
    y_true = [0, 1, 2, 3]
    y_pred = [0, 1, 2, 3]
    classes = ['A', 'B', 'C', 'D']

    result = detailed_evaluation(y_true, y_pred, classes)

    assert result['per_class_f1']['A'] == 1.0
    assert result['per_class_f1']['B'] == 1.0


def test_detailed_evaluation_confusion_matrix():
    """Test confusion matrix in result."""
    y_true = [0, 1, 2]
    y_pred = [0, 1, 2]
    result = detailed_evaluation(y_true, y_pred)

    assert result['confusion_matrix_shape'] == [3, 3]
    # Perfect predictions -> diagonal matrix
    cm = result['confusion_matrix']
    assert cm[0][0] == 1
    assert cm[1][1] == 1
    assert cm[2][2] == 1


def test_calibration_metrics_basic():
    """Test calibration metrics returns expected keys."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_probs = np.array([
        [0.9, 0.05, 0.05],
        [0.85, 0.1, 0.05],
        [0.1, 0.8, 0.1],
        [0.7, 0.2, 0.1],
        [0.1, 0.85, 0.05],
        [0.15, 0.1, 0.75],
    ])

    result = calibration_metrics(y_true, y_probs)

    assert 'expected_calibration_error' in result
    assert 'maximum_calibration_error' in result
    assert 'n_bins' in result
    assert 'per_bin_stats' in result


def test_calibration_metrics_ece_range():
    """Test ECE is in valid range."""
    y_true = [0, 1, 2]
    # Perfect calibration
    y_probs = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])

    result = calibration_metrics(y_true, y_probs, n_bins=10)
    assert result['expected_calibration_error'] == 0.0


def test_calibration_metrics_length_mismatch():
    """Test calibration raises error on length mismatch."""
    y_true = [0, 1, 2]
    y_probs = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ])

    try:
        calibration_metrics(y_true, y_probs)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_confidence_distribution_basic():
    """Test confidence distribution returns expected keys."""
    y_probs = np.array([
        [0.9, 0.05, 0.05],
        [0.85, 0.1, 0.05],
        [0.1, 0.8, 0.1],
    ])

    result = confidence_distribution(y_probs)

    assert 'mean_confidence' in result
    assert 'median_confidence' in result
    assert 'std_confidence' in result
    assert 'low_confidence_samples' in result
    assert 'high_confidence_samples' in result


def test_confidence_distribution_correct_incorrect():
    """Test confidence breakdown by correctness."""
    y_true = np.array([0, 1, 2, 0])
    y_probs = np.array([
        [0.9, 0.05, 0.05],  # correct
        [0.85, 0.1, 0.05],  # correct
        [0.2, 0.3, 0.5],     # incorrect (predicted 2, true 2 actually) - wait that's correct
        [0.1, 0.85, 0.05],   # incorrect
    ])

    # Let's fix the test data: 3 samples, 2 correct, 1 incorrect
    y_true = np.array([0, 1, 2])
    y_probs = np.array([
        [0.9, 0.05, 0.05],  # correct (class 0)
        [0.85, 0.1, 0.05],  # correct (class 1)
        [0.3, 0.3, 0.4],     # incorrect (predicted 2, true 2) - wait that's correct too
    ])

    # Make a clear incorrect case
    y_true = np.array([0, 1, 2])
    y_probs = np.array([
        [0.9, 0.05, 0.05],  # correct
        [0.9, 0.05, 0.05],  # incorrect (predicted 0, true 1)
        [0.9, 0.05, 0.05],  # incorrect (predicted 0, true 2)
    ])

    result = confidence_distribution(y_probs, y_true)

    assert 'correct_mean_confidence' in result
    assert 'incorrect_mean_confidence' in result
    # With same confidence but different correctness, both should exist
    assert 'correct_mean_confidence' in result
    assert 'incorrect_mean_confidence' in result


def test_top_k_accuracy_basic():
    """Test top-k accuracy calculation."""
    y_true = [0, 1, 2]
    y_probs = np.array([
        [0.5, 0.3, 0.2],  # top-1: 0, top-3: [0,1,2]
        [0.3, 0.4, 0.3],  # top-1: 1, top-3: [1,0,2]
        [0.2, 0.3, 0.5],  # top-1: 2, top-3: [2,1,0]
    ])

    result = top_k_accuracy(y_true, y_probs, k=3)
    assert result == 1.0  # All correct in top-3


def test_top_k_accuracy_partial():
    """Test top-k accuracy with partial matches."""
    y_true = [0, 1, 2]
    y_probs = np.array([
        [0.9, 0.05, 0.05],  # top-1: 0 ✓
        [0.9, 0.05, 0.05],  # top-1: 0, true=1 ✗
        [0.9, 0.05, 0.05],  # top-1: 0, true=2 ✗
    ])

    # Top-1 accuracy
    result_1 = top_k_accuracy(y_true, y_probs, k=1)
    assert result_1 == 1/3

    # Top-2 accuracy (should catch the second sample)
    result_2 = top_k_accuracy(y_true, y_probs, k=2)
    assert result_2 == 2/3


def test_consistency_with_basic_metrics():
    """Test that detailed_evaluation is consistent with basic metrics."""
    y_true = [0, 1, 2, 3, 0, 1, 2, 3]
    y_pred = [0, 1, 2, 3, 0, 0, 2, 3]

    # Basic accuracy
    basic_acc = accuracy_score(y_true, y_pred)

    # Detailed accuracy
    detailed = detailed_evaluation(y_true, y_pred)

    assert basic_acc == detailed['accuracy']


def test_empty_input():
    """Test with empty input."""
    y_true: list = []
    y_pred: list = []

    result = detailed_evaluation(y_true, y_pred)
    assert result['accuracy'] == 0.0
    assert result['total_samples'] == 0


if __name__ == "__main__":
    print("Running enhanced metrics tests...")

    test_confusion_matrix_shape()
    print("✓ Confusion matrix shape")

    test_confusion_matrix_values()
    print("✓ Confusion matrix values")

    test_confusion_matrix_single_class()
    print("✓ Confusion matrix single class")

    test_detailed_evaluation_basic()
    print("✓ Detailed evaluation basic")

    test_detailed_evaluation_accuracy()
    print("✓ Detailed evaluation accuracy")

    test_detailed_evaluation_zero_accuracy()
    print("✓ Detailed evaluation zero accuracy")

    test_detailed_evaluation_per_class()
    print("✓ Detailed evaluation per class")

    test_detailed_evaluation_per_class_f1()
    print("✓ Detailed evaluation per class F1")

    test_detailed_evaluation_confusion_matrix()
    print("✓ Detailed evaluation confusion matrix")

    test_calibration_metrics_basic()
    print("✓ Calibration metrics basic")

    test_calibration_metrics_ece_range()
    print("✓ Calibration metrics ECE range")

    test_calibration_metrics_length_mismatch()
    print("✓ Calibration metrics length mismatch")

    test_confidence_distribution_basic()
    print("✓ Confidence distribution basic")

    test_confidence_distribution_correct_incorrect()
    print("✓ Confidence distribution correct/incorrect")

    test_top_k_accuracy_basic()
    print("✓ Top-k accuracy basic")

    test_top_k_accuracy_partial()
    print("✓ Top-k accuracy partial")

    test_consistency_with_basic_metrics()
    print("✓ Consistency with basic metrics")

    test_empty_input()
    print("✓ Empty input")

    print("\n✅ All enhanced metrics tests passed!")
