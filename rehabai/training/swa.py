"""
Stochastic Weight Averaging (SWA) for improved generalization.

SWA averages model weights from multiple points in the training trajectory,
leading to wider optima and better generalization (especially on small datasets).

Reference: "Averaging Weights Leads to Wider Optima and Better Generalization"
           (Izmailov et al., UAI 2018)
"""

import torch
import torch.nn as nn
from torch.optim import Optimizer
from typing import Optional, Callable
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


class SWA:
    """
    Stochastic Weight Averaging implementation.

    Usage:
        swa = SWA(model, swa_start_epoch=10, swa_lr=1e-3)
        # After training:
        swa.swap_weights()
        # Evaluate or use model
        swa.restore_weights()  # If needed
    """

    def __init__(
        self,
        model: nn.Module,
        swa_start_epoch: int = 10,
        swa_lr: float = 1e-3,
        swa_steps_per_epoch: int = 100,
    ):
        self.model = model
        self.swa_start_epoch = swa_start_epoch
        self.swa_lr = swa_lr
        self.swa_steps_per_epoch = swa_steps_per_epoch

        self.swa_weights: Optional[dict] = None
        self.swa_count = 0
        self.ema_weights: Optional[dict] = None
        self.ema_decay = 0.999

    def start_swa(self) -> None:
        """Begin SWA - initialize average weights with current model weights."""
        logger.info(f"Starting SWA from epoch {self.swa_start_epoch}")
        self.swa_weights = deepcopy(self.model.state_dict())
        self.swa_count = 1

        # Also initialize EMA weights
        self.ema_weights = deepcopy(self.model.state_dict())

    def update_swa(self) -> None:
        """
        Update running average of model weights.
        Called after each batch or at regular intervals during SWA phase.
        """
        if self.swa_weights is None:
            return

        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if param.requires_grad and param.data is not None:
                    # Simple average update
                    self.swa_weights[name] = (
                        self.swa_weights[name] * self.swa_count + param.data
                    ) / (self.swa_count + 1)

                    # EMA update (exponentially weighted moving average)
                    if self.ema_weights is not None:
                        self.ema_weights[name] = (
                            self.ema_decay * self.ema_weights[name]
                            + (1 - self.ema_decay) * param.data
                        )

            self.swa_count += 1

    def swap_weights(self, use_ema: bool = False) -> None:
        """
        Replace model weights with SWA averaged weights.

        Args:
            use_ema: If True, use EMA weights instead of simple average
        """
        if use_ema and self.ema_weights is not None:
            logger.info(f"Swapping to EMA weights (count={self.swa_count})")
            self.model.load_state_dict(self.ema_weights)
        elif self.swa_weights is not None:
            logger.info(f"Swapping to SWA weights (count={self.swa_count})")
            self.model.load_state_dict(self.swa_weights)
        else:
            logger.warning("No SWA weights to swap to")

    def restore_weights(self, saved_weights: dict) -> None:
        """
        Restore original model weights.

        Args:
            saved_weights: State dict to restore
        """
        logger.info("Restoring original model weights")
        self.model.load_state_dict(saved_weights)

    def get_swa_lr(self) -> float:
        """Return the learning rate to use during SWA phase."""
        return self.swa_lr


class SWALRScheduler:
    """
    Learning rate scheduler specifically for SWA training.

    Uses a high constant learning rate during SWA phase.
    """

    def __init__(self, optimizer: Optimizer, swa_lr: float = 1e-3):
        self.optimizer = optimizer
        self.swa_lr = swa_lr
        self.swa_started = False

    def step(self, epoch: Optional[int] = None, swa_start: int = 10) -> None:
        """
        Update learning rate.

        Args:
            epoch: Current epoch (used to determine if SWA started)
            swa_start: Epoch at which SWA begins
        """
        if epoch is not None and epoch >= swa_start and not self.swa_started:
            self.swa_started = True
            logger.info(f"SWA started, setting LR to {self.swa_lr}")
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = self.swa_lr

    def swa_started_(self) -> bool:
        """Check if SWA phase has started."""
        return self.swa_started


def apply_swa_bn(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    device: torch.device,
    batches: int = 100
) -> None:
    """
    Update BatchNorm running statistics after SWA weight swap.

    Important: Call this after swap_weights() to ensure proper BN statistics.

    Args:
        model: Model with SWA weights
        dataloader: Training or validation dataloader
        device: Device to run on
        batches: Number of batches to process for BN update
    """
    logger.info("Updating BatchNorm statistics after SWA")
    model.train()
    momenta = {}

    # Save and set momentum to 1.0 for all BatchNorms
    for module in model.modules():
        if isinstance(module, nn.BatchNorm1d) or isinstance(module, nn.BatchNorm2d):
            module.reset_running_stats()
            momenta[module] = module.momentum
            if module.momentum is not None:
                module.momentum = 1.0

    # Forward pass on training data
    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            if i >= batches:
                break

            if isinstance(batch, dict):
                features = batch.get('features')
                if features is None:
                    continue
                features = features.to(device)
                _ = model(features)

    # Restore original momenta
    for module, momentum in momenta.items():
        if momentum is not None:
            module.momentum = momentum

    logger.info("BatchNorm statistics updated")


class EarlyStopping:
    """
    Early stopping with patience for preventing overfitting.

    Tracks validation metric and stops when no improvement for N epochs.
    """

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.001,
        mode: str = 'max',
        verbose: bool = True
    ):
        """
        Args:
            patience: Number of epochs to wait for improvement
            min_delta: Minimum change to qualify as improvement
            mode: 'max' for accuracy/F1, 'min' for loss
            verbose: Print messages when stopping
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.verbose = verbose

        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.best_epoch = 0

    def __call__(self, epoch: int, score: float, model: nn.Module,
                 save_path: str = "best_model.pth") -> bool:
        """
        Check if training should stop.

        Args:
            epoch: Current epoch
            score: Current validation metric
            model: Model to save if improvement
            save_path: Path to save best model

        Returns:
            True if should stop, False otherwise
        """
        if self.best_score is None:
            self.best_score = score
            self.best_epoch = epoch
            self._save_model(model, save_path, score)
            return False

        if self.mode == 'max':
            improved = score > self.best_score + self.min_delta
        else:
            improved = score < self.best_score - self.min_delta

        if improved:
            self.best_score = score
            self.best_epoch = epoch
            self.counter = 0
            self._save_model(model, save_path, score)
            if self.verbose:
                logger.info(f"Epoch {epoch}: Improvement found, best={score:.4f}")
        else:
            self.counter += 1
            if self.verbose:
                logger.info(f"Epoch {epoch}: No improvement ({self.counter}/{self.patience})")

            if self.counter >= self.patience:
                self.early_stop = True
                if self.verbose:
                    logger.info(
                        f"Early stopping triggered at epoch {epoch}. "
                        f"Best was at epoch {self.best_epoch} with score={self.best_score:.4f}"
                    )
                return True

        return False

    def _save_model(self, model: nn.Module, path: str, score: float) -> None:
        """Save model checkpoint."""
        try:
            torch.save({
                'model_state_dict': model.state_dict(),
                'score': score,
                'best_epoch': self.best_epoch
            }, path)
        except Exception as e:
            logger.warning(f"Could not save model: {e}")
