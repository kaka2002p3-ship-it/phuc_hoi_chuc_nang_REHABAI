"""
Enhanced loss functions for multi-task rehabilitation exercise classification.

Includes:
- Focal Loss with class weights
- Label smoothing
- Multi-task weighted loss
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Sequence


class FocalLoss(nn.Module):
    """
    Focal Loss for multi-class classification.

    Focal Loss focuses on hard examples by down-weighting easy examples.
    Reference: Lin et al. "Focal Loss for Dense Object Detection"
    """

    def __init__(
        self,
        alpha: Optional[torch.Tensor] = None,
        gamma: float = 2.0,
        reduction: str = 'mean',
        label_smoothing: float = 0.0,
    ):
        """
        Args:
            alpha: Class weights tensor of shape (num_classes,)
            gamma: Focusing parameter (default: 2.0)
            reduction: 'mean', 'sum', or 'none'
            label_smoothing: Label smoothing factor (default: 0.0)
        """
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        self.label_smoothing = label_smoothing

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            inputs: Logits of shape (batch_size, num_classes)
            targets: Integer class indices of shape (batch_size,)
        """
        num_classes = inputs.size(-1)

        # Apply label smoothing
        if self.label_smoothing > 0:
            targets_smooth = targets.float()
            targets_smooth = (
                targets_smooth * (1 - self.label_smoothing) +
                self.label_smoothing / num_classes
            )
        else:
            targets_smooth = targets.float()

        # Cross entropy loss per sample
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')

        # Probability of the true class
        pt = torch.exp(-ce_loss)

        # Focal loss
        focal_weight = (1 - pt) ** self.gamma
        focal_loss = focal_weight * ce_loss

        # Apply class weights
        if self.alpha is not None:
            if self.alpha.device != inputs.device:
                self.alpha = self.alpha.to(inputs.device)
            alpha_t = self.alpha[targets]
            focal_loss = alpha_t * focal_loss

        # Apply reduction
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class ClassWeightedCrossEntropy(nn.Module):
    """
    Cross Entropy with class weights for imbalanced datasets.
    """

    def __init__(
        self,
        weights: Optional[torch.Tensor] = None,
        label_smoothing: float = 0.0,
        reduction: str = 'mean',
    ):
        super().__init__()
        self.weights = weights
        self.label_smoothing = label_smoothing
        self.reduction = reduction

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        return F.cross_entropy(
            inputs,
            targets,
            weight=self.weights,
            label_smoothing=self.label_smoothing,
            reduction=self.reduction,
        )


class CombinedLoss(nn.Module):
    """
    Combines multiple losses with learnable or fixed weights.

    For multi-task learning:
    - Exercise classification loss
    - Completion/rehabilitation score loss
    """

    def __init__(
        self,
        task_losses: list[nn.Module],
        task_weights: Optional[list[float]] = None,
        learnable_weights: bool = False,
    ):
        """
        Args:
            task_losses: List of loss modules for each task
            task_weights: Initial weights for each task (default: equal)
            learnable_weights: If True, weights are learnable parameters
        """
        super().__init__()
        self.task_losses = nn.ModuleList(task_losses)

        if task_weights is None:
            task_weights = [1.0] * len(task_losses)

        if learnable_weights:
            # Learnable weights (log space for stability)
            self.log_weights = nn.Parameter(torch.log(torch.tensor(task_weights)))
        else:
            self.register_buffer('weights', torch.tensor(task_weights))

    @property
    def weights(self) -> torch.Tensor:
        if hasattr(self, 'log_weights'):
            return torch.exp(self.log_weights) / torch.exp(self.log_weights).sum()
        return self._buffers.get('weights', torch.ones(len(self.task_losses)))

    def forward(
        self,
        predictions: list[torch.Tensor],
        targets: list[torch.Tensor],
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """
        Args:
            predictions: List of predictions for each task
            targets: List of targets for each task

        Returns:
            Combined loss and dict of individual task losses
        """
        total_loss = 0.0
        task_losses = {}

        for i, (pred, target, loss_fn) in enumerate(
            zip(predictions, targets, self.task_losses)
        ):
            task_loss = loss_fn(pred, target)
            total_loss = total_loss + self.weights[i] * task_loss
            task_losses[f'task_{i}'] = task_loss.item()

        return total_loss, task_losses


class AsymmetricLoss(nn.Module):
    """
    Asymmetric Loss for handling class imbalance with positive/negative asymmetry.

    Reference: Based on papers:
    - "Asymmetric Loss for Multi-Label Classification"
    - Tailors well for rehabilitation where "incomplete" might be minority class
    """

    def __init__(
        self,
        gamma_pos: float = 0.0,
        gamma_neg: float = 4.0,
        clip: float = 0.05,
    ):
        """
        Args:
            gamma_pos: Focusing parameter for positive (hard) examples
            gamma_neg: Focusing parameter for negative (easy) examples
            clip: Minimum probability to consider (prevents overflow)
        """
        super().__init__()
        self.gamma_pos = gamma_pos
        self.gamma_neg = gamma_neg
        self.clip = clip

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Get probabilities
        p = torch.sigmoid(inputs)
        targets_one_hot = F.one_hot(targets, inputs.size(-1)).float()

        # Binary cross entropy
        bce = F.binary_cross_entropy_with_logits(inputs, targets_one_hot, reduction='none')

        # Asymmetric clipping
        p_m = p.clamp(min=self.clip, max=1.0 - self.clip)

        # Modulating factor
        modulator_pos = (1 - p_m) ** self.gamma_pos
        modulator_neg = p_m ** self.gamma_neg

        # Combine
        loss = targets_one_hot * modulator_pos * bce + (1 - targets_one_hot) * modulator_neg * bce

        return loss.mean()


def compute_class_weights(
    labels: list[int] | torch.Tensor,
    num_classes: int,
    method: str = 'balanced',
) -> torch.Tensor:
    """
    Compute class weights for imbalanced datasets.

    Args:
        labels: List or tensor of class labels
        num_classes: Number of classes
        method: 'balanced', 'effective', or 'custom'

    Returns:
        Tensor of class weights
    """
    if isinstance(labels, list):
        labels = torch.tensor(labels)

    class_counts = torch.bincount(labels, minlength=num_classes).float()

    if method == 'balanced':
        # n_samples / (n_classes * n_samples_per_class)
        weights = len(labels) / (num_classes * class_counts)
    elif method == 'effective':
        # Effective number of samples
        beta = 0.9999
        effective_num = 1.0 - torch.pow(beta, class_counts)
        weights = (1.0 - beta) / effective_num
    else:
        weights = torch.ones(num_classes)

    # Handle zero counts
    weights[class_counts == 0] = 0.0

    # Normalize
    weights = weights / weights.sum() * num_classes

    return weights


class DynamicLossWeighting(nn.Module):
    """
    Dynamically adjusts task weights based on training progress.

    Uses uncertainty-based weighting from:
    "Multi-Task Learning Using Uncertainty to Weigh Losses"
    """

    def __init__(self, num_tasks: int, initial_log_var: float = 0.0):
        """
        Args:
            num_tasks: Number of tasks
            initial_log_var: Initial log variance (controls uncertainty)
        """
        super().__init__()
        self.log_vars = nn.Parameter(torch.zeros(num_tasks) + initial_log_var)

    def forward(
        self,
        losses: list[torch.Tensor],
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """
        Args:
            losses: List of task losses

        Returns:
            Weighted combined loss and individual losses for logging
        """
        total_loss = 0.0
        task_losses = {}

        for i, loss in enumerate(losses):
            precision = torch.exp(-self.log_vars[i])
            weighted_loss = precision * loss + self.log_vars[i]
            total_loss = total_loss + weighted_loss
            task_losses[f'task_{i}_loss'] = loss.item()
            task_losses[f'task_{i}_weight'] = precision.item()

        return total_loss, task_losses
