import numpy as np

from shared.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
)


def test_multiclass_macro_metrics_with_explicit_labels():
    y_true = [0, 0, 1, 1, 2]
    y_pred = [0, 1, 1, 1, 0]
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2, 3]
    )
    np.testing.assert_allclose(precision, [0.5, 2 / 3, 0.0, 0.0])
    np.testing.assert_allclose(recall, [0.5, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(f1, [0.5, 0.8, 0.0, 0.0])
    np.testing.assert_array_equal(support, [2, 2, 1, 0])
    assert accuracy_score(y_true, y_pred) == 0.6
    assert f1_score(y_true, y_pred, average="macro", labels=[0, 1, 2, 3]) == 0.325
    assert precision_score(y_true, y_pred, average="macro", labels=[0, 1, 2, 3]) == (0.5 + 2 / 3) / 4
    assert recall_score(y_true, y_pred, average="macro", labels=[0, 1, 2, 3]) == 0.375


def test_empty_metrics_are_fail_safe():
    assert accuracy_score([], []) == 0.0
    assert f1_score([], [], average="macro", labels=[0, 1]) == 0.0
