"""
Advanced loss functions for training with regularization to prevent overfitting.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple


class LabelSmoothingCrossEntropy(nn.Module):
    """
    Cross Entropy Loss with Label Smoothing.

    Reduces overconfidence and improves generalization by softening targets.
    For 4-class: smoothing 0.1 means targets become [0.033, 0.033, 0.9, 0.033] instead of [0, 0, 1, 0]

    Reference: "Rethinking the Inception Architecture for Computer Vision" (Szegedy et al.)
    """

    def __init__(self, smoothing: float = 0.1, reduction: str = 'mean'):
        """
        Args:
            smoothing: Label smoothing factor (0.0 = no smoothing, 0.1 = recommended)
            reduction: 'none', 'mean', or 'sum'
        """
        super().__init__()
        self.smoothing = smoothing
        self.reduction = reduction

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            inputs: (B, C) logits
            targets: (B,) integer labels
        """
        num_classes = inputs.size(-1)

        # Convert targets to one-hot
        one_hot = torch.zeros_like(inputs).scatter(1, targets.unsqueeze(1), 1)

        # Apply label smoothing
        smoothed = one_hot * (1 - self.smoothing) + self.smoothing / num_classes

        # Compute cross entropy with soft targets
        log_probs = F.log_softmax(inputs, dim=-1)

        loss = -(smoothed * log_probs).sum(dim=-1)

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        return loss


class LabelSmoothingFocalLoss(nn.Module):
    """
    Combines Label Smoothing with Focal Loss for better calibration and hard example mining.

    Best for imbalanced datasets with overfitting concerns.
    """

    def __init__(
        self,
        smoothing: float = 0.1,
        alpha: Optional[torch.Tensor] = None,
        gamma: float = 2.0,
        reduction: str = 'mean'
    ):
        super().__init__()
        self.smoothing = smoothing
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        num_classes = inputs.size(-1)

        # Label smoothing
        one_hot = torch.zeros_like(inputs).scatter(1, targets.unsqueeze(1), 1)
        smoothed = one_hot * (1 - self.smoothing) + self.smoothing / num_classes

        # Focal component
        log_probs = F.log_softmax(inputs, dim=-1)
        ce_loss = -(smoothed * log_probs).sum(dim=-1)

        pt = torch.exp(-ce_loss)
        focal_weight = (1 - pt) ** self.gamma

        # Class weights
        if self.alpha is not None:
            if self.alpha.device != inputs.device:
                self.alpha = self.alpha.to(inputs.device)
            focal_weight = focal_weight * self.alpha[targets]

        loss = focal_weight * ce_loss

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        return loss


class MixUpLoss(nn.Module):
    """
    Loss function for MixUp augmentation.

    MixUp creates virtual training examples by mixing pairs of examples:
    x' = λxᵢ + (1-λ)xⱼ
    y' = λyᵢ + (1-λ)yⱼ

    This acts as a powerful regularizer and reduces overfitting.

    Reference: "mixup: Beyond Empirical Risk Minimization" (Zhang et al.)
    """

    def __init__(self, base_criterion: nn.Module = None, smoothing: float = 0.1):
        super().__init__()
        self.base_criterion = base_criterion or LabelSmoothingCrossEntropy(smoothing=smoothing)

    def forward(
        self,
        inputs: torch.Tensor,
        targets_a: torch.Tensor,
        targets_b: torch.Tensor,
        lam: float
    ) -> torch.Tensor:
        """
        Args:
            inputs: Mixed logits from model
            targets_a: Original labels
            targets_b: Mixed labels
            lam: MixUp lambda
        """
        return lam * self.base_criterion(inputs, targets_a) + (1 - lam) * self.base_criterion(inputs, targets_b)


class CutMixLoss(nn.Module):
    """
    Loss function for CutMix augmentation.

    Similar to MixUp but cuts and pastes patches between images.
    Encourages model to learn from local features rather than global patterns.

    Reference: "CutMix: Regularization Strategy to Train Strong Classifiers" (Yun et al.)
    """

    def __init__(self, base_criterion: nn.Module = None, smoothing: float = 0.1):
        super().__init__()
        self.base_criterion = base_criterion or LabelSmoothingCrossEntropy(smoothing=smoothing)

    def forward(
        self,
        inputs: torch.Tensor,
        targets_a: torch.Tensor,
        targets_b: torch.Tensor,
        lam: float
    ) -> torch.Tensor:
        """Same interface as MixUpLoss for compatibility."""
        return lam * self.base_criterion(inputs, targets_a) + (1 - lam) * self.base_criterion(inputs, targets_b)


def mixup_data(
    x: torch.Tensor,
    y: torch.Tensor,
    alpha: float = 0.4
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """
    Apply MixUp augmentation to a batch.

    Args:
        x: Input tensor (B, T, F) or (B, C, H, W)
        y: Labels (B,)
        alpha: Beta distribution parameter (higher = more interpolation)

    Returns:
        Mixed inputs, labels_a, labels_b, lambda

    Example:
        >>> mixed_x, y_a, y_b, lam = mixup_data(x, y, alpha=0.4)
        >>> outputs = model(mixed_x)
        >>> loss = mixup_criterion(outputs, y_a, y_b, lam)
    """
    if alpha > 0:
        lam = torch.distributions.Beta(alpha, alpha).sample()
    else:
        lam = 1.0

    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(x.device)

    # Ensure mixing between different samples
    if lam < 0.5:
        lam = 1 - lam
        index = index

    mixed_x = lam * x + (1 - lam) * x[index]

    return mixed_x, y, y[index], lam


def cutmix_data(
    x: torch.Tensor,
    y: torch.Tensor,
    alpha: float = 1.0
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """
    Apply CutMix augmentation to a batch.

    Args:
        x: Input tensor (B, T, F) - motion sequences
        y: Labels (B,)
        alpha: Beta distribution parameter

    Returns:
        Mixed inputs, labels_a, labels_b, lambda
    """
    if alpha > 0:
        lam = torch.distributions.Beta(alpha, alpha).sample()
    else:
        lam = 1.0

    batch_size, seq_len, feat_dim = x.size()
    index = torch.randperm(batch_size).to(x.device)

    # For motion sequences, we cut a contiguous temporal region
    cut_len = int(lam * seq_len)
    cut_start = torch.randint(0, max(1, seq_len - cut_len), (1,)).item()

    mixed_x = x.clone()
    mixed_x[:, cut_start:cut_start + cut_len, :] = x[index, cut_start:cut_start + cut_len, :]

    # Adjust lambda based on actual cut size
    lam = 1 - cut_len / seq_len

    return mixed_x, y, y[index], lam
