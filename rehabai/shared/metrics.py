"""Small dependency-free classification metrics used by research scripts.

The project intentionally keeps evaluation runnable on Windows machines where a
binary scikit-learn installation may be unavailable or blocked by policy.  The
functions below implement the subset of the sklearn API used by the trainers.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Dict, Any, Optional
from collections import defaultdict

import numpy as np


def _arrays(y_true: Iterable, y_pred: Iterable) -> tuple[np.ndarray, np.ndarray]:
    true = np.asarray(list(y_true))
    pred = np.asarray(list(y_pred))
    if true.shape != pred.shape:
        raise ValueError(f"y_true and y_pred must have the same shape, got {true.shape} and {pred.shape}")
    return true, pred


def accuracy_score(y_true: Iterable, y_pred: Iterable) -> float:
    true, pred = _arrays(y_true, y_pred)
    return float(np.mean(true == pred)) if true.size else 0.0


def _class_counts(true: np.ndarray, pred: np.ndarray, labels: Sequence) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    precision, recall, f1, support = [], [], [], []
    for label in labels:
        actual = true == label
        guessed = pred == label
        tp = int(np.sum(actual & guessed))
        fp = int(np.sum(~actual & guessed))
        fn = int(np.sum(actual & ~guessed))
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        score = 2 * p * r / (p + r) if p + r else 0.0
        precision.append(p)
        recall.append(r)
        f1.append(score)
        support.append(int(np.sum(actual)))
    return (np.asarray(precision, dtype=float), np.asarray(recall, dtype=float),
            np.asarray(f1, dtype=float), np.asarray(support, dtype=int))


def precision_recall_fscore_support(
    y_true: Iterable,
    y_pred: Iterable,
    *,
    average: str | None = None,
    zero_division: int | float = 0,
    labels: Sequence | None = None,
):
    true, pred = _arrays(y_true, y_pred)
    if labels is None:
        labels = np.unique(np.concatenate([true, pred])) if true.size or pred.size else np.asarray([])
    p, r, f1, support = _class_counts(true, pred, labels)
    if average == "macro":
        return float(np.mean(p)) if p.size else 0.0, float(np.mean(r)) if r.size else 0.0, float(np.mean(f1)) if f1.size else 0.0, None
    if average is None:
        return p, r, f1, support
    raise ValueError(f"Unsupported average={average!r}; use None or 'macro'.")


def f1_score(y_true: Iterable, y_pred: Iterable, *, average: str = "binary", zero_division: int | float = 0, labels: Sequence | None = None) -> float:
    if average == "macro":
        return float(precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=zero_division, labels=labels)[2])
    if average == "binary":
        labels = [1] if labels is None else labels
        return float(precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=zero_division, labels=labels)[2][0])
    raise ValueError(f"Unsupported average={average!r}")


def precision_score(y_true: Iterable, y_pred: Iterable, *, average: str = "binary", zero_division: int | float = 0, labels: Sequence | None = None) -> float:
    if average != "macro":
        raise ValueError("This implementation supports precision_score(..., average='macro') only.")
    return float(precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=zero_division, labels=labels)[0])


def recall_score(y_true: Iterable, y_pred: Iterable, *, average: str = "binary", zero_division: int | float = 0, labels: Sequence | None = None) -> float:
    if average != "macro":
        raise ValueError("This implementation supports recall_score(..., average='macro') only.")
    return float(precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=zero_division, labels=labels)[1])


# =============================================================================
# Enhanced Evaluation Functions (NEW)
# =============================================================================

def confusion_matrix(y_true: Iterable, y_pred: Iterable) -> np.ndarray:
    """
    Compute confusion matrix for multi-class classification.

    Returns:
        2D array of shape (n_classes, n_classes) where
        confusion[i, j] = number of samples with true label i predicted as j
    """
    true, pred = _arrays(y_true, y_pred)
    labels = np.unique(np.concatenate([true, pred])) if true.size else np.asarray([])

    n = len(labels)
    matrix = np.zeros((n, n), dtype=int)

    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    for t, p in zip(true, pred):
        t_idx = label_to_idx.get(t, -1)
        p_idx = label_to_idx.get(p, -1)
        if t_idx >= 0 and p_idx >= 0:
            matrix[t_idx, p_idx] += 1

    return matrix


def detailed_evaluation(
    y_true: Iterable,
    y_pred: Iterable,
    class_names: Optional[Sequence[str]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive evaluation with per-class metrics, confusion matrix,
    and summary statistics.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Optional list of class names (must match unique labels)

    Returns:
        Dictionary containing:
        - accuracy: Overall accuracy
        - macro_precision, macro_recall, macro_f1: Macro-averaged metrics
        - per_class: Dict with precision, recall, f1, support for each class
        - confusion_matrix: 2D array
        - per_class_f1: Simple dict of class_name -> f1_score
        - summary: Human-readable summary
    """
    true, pred = _arrays(y_true, y_pred)
    unique_labels = np.unique(np.concatenate([true, pred])) if true.size else np.asarray([])

    # Default class names if not provided
    if class_names is None:
        class_names = [f"Class_{i}" for i in unique_labels]
    elif len(class_names) < len(unique_labels):
        class_names = list(class_names) + [f"Class_{i}" for i in unique_labels[len(class_names):]]

    # Compute per-class metrics
    precision, recall, f1, support = _class_counts(true, pred, unique_labels)

    per_class = {}
    per_class_f1 = {}
    for i, label in enumerate(unique_labels):
        name = class_names[i] if i < len(class_names) else f"Class_{label}"
        per_class[name] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1_score": float(f1[i]),
            "support": int(support[i]),
        }
        per_class_f1[name] = float(f1[i])

    # Compute confusion matrix
    conf_matrix = confusion_matrix(true, pred)

    # Compute macro averages
    macro_precision = float(np.mean(precision)) if precision.size else 0.0
    macro_recall = float(np.mean(recall)) if recall.size else 0.0
    macro_f1 = float(np.mean(f1)) if f1.size else 0.0
    overall_accuracy = float(np.mean(true == pred)) if true.size else 0.0

    # Generate summary string
    summary = (
        f"Accuracy: {overall_accuracy:.2%} | "
        f"Macro F1: {macro_f1:.4f} | "
        f"Macro Precision: {macro_precision:.4f} | "
        f"Macro Recall: {macro_recall:.4f}"
    )

    return {
        "accuracy": overall_accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "per_class_f1": per_class_f1,
        "confusion_matrix": conf_matrix.tolist(),
        "confusion_matrix_shape": list(conf_matrix.shape),
        "summary": summary,
        "total_samples": int(len(true)),
    }


def calibration_metrics(
    y_true: Iterable,
    y_probs: np.ndarray,
    n_bins: int = 10
) -> Dict[str, Any]:
    """
    Compute calibration metrics (ECE, MCE) to assess prediction confidence.

    Args:
        y_true: Ground truth labels
        y_probs: Predicted probabilities, shape (n_samples, n_classes)
        n_bins: Number of confidence bins for ECE calculation

    Returns:
        Dict with ECE, MCE, and per-bin statistics
    """
    true = np.asarray(list(y_true))
    if len(true) != len(y_probs):
        raise ValueError("y_true and y_probs must have same length")

    n_samples, n_classes = y_probs.shape
    max_probs = np.max(y_probs, axis=1)
    predictions = np.argmax(y_probs, axis=1)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    bin_stats = []

    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]
        in_bin = (max_probs > bin_lower) & (max_probs <= bin_upper if i < n_bins - 1 else True)

        if np.sum(in_bin) > 0:
            bin_acc = np.mean(predictions[in_bin] == true[in_bin])
            bin_conf = np.mean(max_probs[in_bin])
            bin_weight = np.sum(in_bin) / n_samples
            bin_ece = bin_weight * abs(bin_acc - bin_conf)
            ece += bin_ece
            mce = max(mce, abs(bin_acc - bin_conf))

            bin_stats.append({
                "bin": i,
                "confidence_range": f"[{bin_lower:.1f}, {bin_upper:.1f})",
                "count": int(np.sum(in_bin)),
                "accuracy": float(bin_acc),
                "avg_confidence": float(bin_conf),
                "ece_contribution": float(bin_ece),
            })

    return {
        "expected_calibration_error": float(ece),
        "maximum_calibration_error": float(mce),
        "n_bins": n_bins,
        "per_bin_stats": bin_stats,
    }


def confidence_distribution(
    y_probs: np.ndarray,
    y_true: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Analyze the distribution of prediction confidence scores.

    Args:
        y_probs: Predicted probabilities, shape (n_samples, n_classes)
        y_true: Optional ground truth for correct/incorrect breakdown

    Returns:
        Dict with confidence statistics and histograms
    """
    max_probs = np.max(y_probs, axis=1)
    predictions = np.argmax(y_probs, axis=1)

    stats = {
        "mean_confidence": float(np.mean(max_probs)),
        "median_confidence": float(np.median(max_probs)),
        "std_confidence": float(np.std(max_probs)),
        "min_confidence": float(np.min(max_probs)),
        "max_confidence": float(np.max(max_probs)),
        "low_confidence_samples": int(np.sum(max_probs < 0.5)),
        "high_confidence_samples": int(np.sum(max_probs >= 0.9)),
    }

    if y_true is not None:
        correct = predictions == y_true
        if np.sum(correct) > 0:
            stats["correct_mean_confidence"] = float(np.mean(max_probs[correct]))
        if np.sum(~correct) > 0:
            stats["incorrect_mean_confidence"] = float(np.mean(max_probs[~correct]))

    return stats


def top_k_accuracy(
    y_true: Iterable,
    y_probs: np.ndarray,
    k: int = 3
) -> float:
    """
    Compute top-k accuracy (prediction is correct if true label is in top-k predictions).

    Args:
        y_true: Ground truth labels
        y_probs: Predicted probabilities, shape (n_samples, n_classes)
        k: Number of top predictions to consider

    Returns:
        Top-k accuracy as float
    """
    true = np.asarray(list(y_true))
    top_k_preds = np.argsort(y_probs, axis=1)[:, -k:]
    hits = np.any(top_k_preds == true.reshape(-1, 1), axis=1)
    return float(np.mean(hits))
