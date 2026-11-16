"""
Regularized Training Script for RehabAI.

This script implements advanced regularization techniques to reduce overfitting:
1. Label Smoothing - Prevents overconfident predictions
2. MixUp - Data augmentation by interpolating examples
3. SWA - Stochastic Weight Averaging for wider optima
4. Early Stopping - Prevents overfitting
5. Data Augmentation - Domain-specific pose augmentations

Usage:
    python training/train_regularized.py \
        --train-manifest data/stage3_upper_limb/loso/fold_01/train_manifest.csv \
        --val-manifest data/stage3_upper_limb/loso/fold_01/val_manifest.csv \
        --norm-json data/stage3_upper_limb/norm/fold_01/normalization.json \
        --fold-id fold_01 \
        --epochs 50
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import numpy as np
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.device import select_training_device
from training.datasets.rehab_dataset import RehabDataset
from training.models.cnn_transformer import RehabModel
from training.losses.advanced_losses import (
    LabelSmoothingCrossEntropy,
    LabelSmoothingFocalLoss,
    MixUpLoss,
    mixup_data,
    cutmix_data,
)
from training.swa import SWA, SWALRScheduler, apply_swa_bn, EarlyStopping
from training.augmentation.advanced_augmentation import AdvancedAugmentation
from shared.metrics import accuracy_score, f1_score, precision_score, recall_score


def parse_args():
    parser = argparse.ArgumentParser(description="Regularized training for RehabAI")
    parser.add_argument("--data_dir", type=str, default="data/processed/keypoints")
    parser.add_argument("--train-manifest", type=str, required=True)
    parser.add_argument("--val-manifest", type=str, required=True)
    parser.add_argument("--norm-json", type=str, required=True)
    parser.add_argument("--fold-id", type=str, required=True)
    parser.add_argument("--source-dir", type=str, required=True)

    # Training params
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-4)

    # Regularization params
    parser.add_argument("--label_smoothing", type=float, default=0.1,
                        help="Label smoothing factor (0.0-0.2 recommended)")
    parser.add_argument("--mixup_alpha", type=float, default=0.4,
                        help="MixUp alpha parameter (0.2-0.6 recommended)")
    parser.add_argument("--use_mixup", action="store_true", default=True,
                        help="Enable MixUp augmentation")
    parser.add_argument("--use_cutmix", action="store_true",
                        help="Enable CutMix augmentation (alternative to MixUp)")
    parser.add_argument("--dropout", type=float, default=0.3,
                        help="Dropout rate for model")

    # SWA params
    parser.add_argument("--use_swa", action="store_true", default=True,
                        help="Enable Stochastic Weight Averaging")
    parser.add_argument("--swa_start_epoch", type=int, default=20,
                        help="Epoch to start SWA")
    parser.add_argument("--swa_lr", type=float, default=5e-4,
                        help="Learning rate during SWA phase")

    # Early stopping
    parser.add_argument("--patience", type=int, default=15,
                        help="Early stopping patience")

    # Class balancing
    parser.add_argument("--num-classes", type=int, default=4)
    parser.add_argument("--class_weights", type=str, default=None,
                        help="Path to class weights JSON")

    return parser.parse_args()


def compute_class_weights(loader: DataLoader, num_classes: int) -> Optional[torch.Tensor]:
    """Compute inverse frequency class weights."""
    class_counts = [0] * num_classes
    total = 0

    for batch in loader:
        labels = batch['exercise'].numpy()
        for label in labels:
            class_counts[label] += 1
            total += 1

    if total == 0:
        return None

    weights = []
    for count in class_counts:
        if count > 0:
            weights.append(total / (num_classes * count))
        else:
            weights.append(1.0)

    weights = np.array(weights)
    weights = weights / weights.sum() * num_classes  # Normalize

    return torch.tensor(weights, dtype=torch.float32)


def train_epoch_regularized(
    model,
    dataloader,
    criterion,
    optimizer,
    device,
    scaler,
    use_mixup: bool = False,
    mixup_alpha: float = 0.4,
    use_cutmix: bool = False,
):
    """Train one epoch with MixUp/CutMix augmentation."""
    model.train()
    running_loss = 0.0
    all_preds = []
    all_labels = []

    pbar = tqdm(dataloader, desc="Training")
    for batch in pbar:
        features = batch['features'].to(device)
        labels = batch['exercise'].to(device)

        optimizer.zero_grad()

        # Apply MixUp or CutMix with probability
        apply_mixup = use_mixup and np.random.random() < 0.5
        apply_cutmix = use_cutmix and np.random.random() < 0.3

        if apply_cutmix:
            features, labels_a, labels_b, lam = cutmix_data(features, labels, alpha=0.5)
        elif apply_mixup:
            features, labels_a, labels_b, lam = mixup_data(features, labels, alpha=mixup_alpha)
        else:
            labels_a, labels_b, lam = labels, labels, 1.0

        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            outputs = model(features)

            if apply_mixup or apply_cutmix:
                # MixUp loss
                loss_a = criterion(outputs, labels_a)
                loss_b = criterion(outputs, labels_b)
                loss = lam * loss_a + (1 - lam) * loss_b
            else:
                loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()

        # For metrics, use original labels
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(labels.cpu().numpy())

        pbar.set_postfix({"loss": f"{loss.item():.4f}"})

    epoch_loss = running_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)

    return epoch_loss, acc, f1


def validate(model, dataloader, criterion, device):
    """Validate model."""
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Validation"):
            features = batch['features'].to(device)
            labels = batch['exercise'].to(device)

            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                outputs = model(features)
                loss = criterion(outputs, labels)

            running_loss += loss.item()

            probs = torch.softmax(outputs, dim=1).cpu().numpy()
            preds = np.argmax(probs, axis=1)
            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs)

    epoch_loss = running_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)

    return {
        'loss': epoch_loss,
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
        'predictions': all_preds,
        'labels': all_labels,
        'probabilities': all_probs,
    }


def main():
    args = parse_args()
    device = select_training_device()
    print(f"Using device: {device}")

    # Validation
    if "extraction_quality" in args.train_manifest:
        raise ValueError("Cannot use extraction_quality.csv as a training manifest.")
    if not os.path.exists(args.norm_json):
        raise FileNotFoundError(f"Missing normalization JSON: {args.norm_json}")

    # Create datasets
    print("Loading datasets...")
    train_dataset = RehabDataset(
        data_dir=args.data_dir,
        source_dir=args.source_dir,
        split_manifest_csv=args.train_manifest,
        split='train',
        normalization_json=args.norm_json,
        fold_id=args.fold_id,
        apply_augmentation=True,
    )
    val_dataset = RehabDataset(
        data_dir=args.data_dir,
        source_dir=args.source_dir,
        split_manifest_csv=args.val_manifest,
        split='val',
        normalization_json=args.norm_json,
        fold_id=args.fold_id,
        apply_augmentation=False,
    )

    if len(train_dataset) == 0:
        raise ValueError("Train dataset is empty.")
    if len(val_dataset) == 0:
        raise ValueError("Val dataset is empty.")

    print(f"Train size: {len(train_dataset)}, Val size: {len(val_dataset)}")

    # Compute class weights if not provided
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=min(4, os.cpu_count() or 1),
        pin_memory=True,
    )

    class_weights = None
    if args.class_weights:
        import json
        with open(args.class_weights) as f:
            weights = json.load(f)
        class_weights = torch.tensor(weights, dtype=torch.float32).to(device)
    else:
        # Compute from training data
        computed_weights = compute_class_weights(train_loader, args.num_classes)
        if computed_weights is not None:
            class_weights = computed_weights.to(device)
            print(f"Computed class weights: {class_weights.tolist()}")

    # Create model
    model = RehabModel(num_classes=args.num_classes).to(device)

    # Add dropout if specified (modify model if needed)
    # Note: This assumes the model supports dropout rate parameter
    if hasattr(model, 'dropout_rate'):
        model.dropout_rate = args.dropout

    # Loss function with label smoothing
    if args.label_smoothing > 0:
        criterion = LabelSmoothingCrossEntropy(
            smoothing=args.label_smoothing,
            reduction='mean'
        )
        print(f"Using Label Smoothing: {args.label_smoothing}")
    else:
        criterion = nn.CrossEntropyLoss(weight=class_weights)

    val_criterion = nn.CrossEntropyLoss()

    # Optimizer with weight decay
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    # Scheduler: Cosine annealing then SWA
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.swa_start_epoch)
    swa_scheduler = SWALRScheduler(optimizer, swa_lr=args.swa_lr)

    # Mixed precision
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == 'cuda')

    # SWA
    swa = SWA(
        model,
        swa_start_epoch=args.swa_start_epoch,
        swa_lr=args.swa_lr,
    )

    # Early stopping
    early_stopping = EarlyStopping(
        patience=args.patience,
        min_delta=0.001,
        mode='max',
        verbose=True,
    )

    # Logging
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f"data/models/logs/regularized_{args.fold_id}_{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(log_dir=str(log_dir))

    save_dir = Path(f"data/models/weights/regularized_{args.fold_id}")
    save_dir.mkdir(parents=True, exist_ok=True)

    # SWA dataloader (may need to iterate multiple times)
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=min(4, os.cpu_count() or 1),
        pin_memory=True,
    )

    print("\n" + "=" * 60)
    print("Starting Regularized Training")
    print(f"  Label Smoothing: {args.label_smoothing}")
    print(f"  MixUp: {args.use_mixup} (alpha={args.mixup_alpha})")
    print(f"  CutMix: {args.use_cutmix}")
    print(f"  SWA: {args.use_swa} (start={args.swa_start_epoch}, lr={args.swa_lr})")
    print(f"  Early Stopping: patience={args.patience}")
    print(f"  Weight Decay: {args.weight_decay}")
    print("=" * 60 + "\n")

    best_f1 = 0.0
    swa_started = False

    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")
        print("-" * 40)

        # Check if SWA should start
        if epoch == args.swa_start_epoch and args.use_swa:
            swa.start_swa()
            swa_started = True
            print(f"→ SWA started at epoch {epoch + 1}")

        # Update learning rate
        if swa_started:
            swa_scheduler.step(epoch=epoch, swa_start=args.swa_start_epoch)
        else:
            scheduler.step()

        current_lr = optimizer.param_groups[0]['lr']
        print(f"Learning Rate: {current_lr:.6f}")

        # Training
        if swa_started and args.use_swa:
            # During SWA, update weights after each batch
            train_loss, train_acc, train_f1 = train_epoch_regularized(
                model, train_loader, criterion, optimizer, device, scaler,
                use_mixup=args.use_mixup,
                mixup_alpha=args.mixup_alpha,
                use_cutmix=args.use_cutmix,
            )
            # Update SWA weights
            swa.update_swa()
        else:
            train_loss, train_acc, train_f1 = train_epoch_regularized(
                model, train_loader, criterion, optimizer, device, scaler,
                use_mixup=args.use_mixup,
                mixup_alpha=args.mixup_alpha,
                use_cutmix=args.use_cutmix,
            )

        # Validation
        val_metrics = validate(model, val_loader, val_criterion, device)

        # Logging
        writer.add_scalar("Loss/Train", train_loss, epoch)
        writer.add_scalar("Loss/Val", val_metrics['loss'], epoch)
        writer.add_scalar("Metric/Train_Accuracy", train_acc, epoch)
        writer.add_scalar("Metric/Train_F1", train_f1, epoch)
        writer.add_scalar("Metric/Val_Accuracy", val_metrics['accuracy'], epoch)
        writer.add_scalar("Metric/Val_F1", val_metrics['f1'], epoch)
        writer.add_scalar("Metric/Val_Precision", val_metrics['precision'], epoch)
        writer.add_scalar("Metric/Val_Recall", val_metrics['recall'], epoch)
        writer.add_scalar("LR", current_lr, epoch)

        print(f"Train - Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, F1: {train_f1:.4f}")
        print(f"Val   - Loss: {val_metrics['loss']:.4f}, Acc: {val_metrics['accuracy']:.4f}, "
              f"F1: {val_metrics['f1']:.4f}, Prec: {val_metrics['precision']:.4f}, Rec: {val_metrics['recall']:.4f}")

        # Save best model (before SWA swap)
        if val_metrics['f1'] >= best_f1:
            best_f1 = val_metrics['f1']
            best_path = save_dir / "best_regularized.pth"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_metrics['f1'],
                'val_acc': val_metrics['accuracy'],
                'config': {
                    'label_smoothing': args.label_smoothing,
                    'mixup_alpha': args.mixup_alpha,
                    'use_swa': args.use_swa,
                    'swa_count': swa.swa_count if swa_started else 0,
                }
            }, best_path)
            print(f"✓ Saved best model (F1={val_metrics['f1']:.4f})")

        # Early stopping check (only before SWA)
        if not swa_started:
            should_stop = early_stopping(epoch, val_metrics['f1'], model)
            if should_stop and not args.use_swa:
                print(f"\nEarly stopping triggered at epoch {epoch + 1}")
                break

    # After training, apply SWA if used
    if args.use_swa and swa.swa_count > 1:
        print("\n" + "=" * 60)
        print("Applying SWA weights...")
        print("=" * 60)

        # Swap to SWA weights
        swa.swap_weights(use_ema=True)

        # Update BN statistics
        apply_swa_bn(model, train_loader, device, batches=50)

        # Validate with SWA weights
        swa_val_metrics = validate(model, val_loader, val_criterion, device)
        print(f"SWA Val - Loss: {swa_val_metrics['loss']:.4f}, Acc: {swa_val_metrics['accuracy']:.4f}, "
              f"F1: {swa_val_metrics['f1']:.4f}")

        # Save SWA model if better
        if swa_val_metrics['f1'] > best_f1:
            print(f"✓ SWA model is better! F1: {swa_val_metrics['f1']:.4f}")
            swa_path = save_dir / "best_swa.pth"
            torch.save({
                'model_state_dict': model.state_dict(),
                'val_f1': swa_val_metrics['f1'],
                'val_acc': swa_val_metrics['accuracy'],
                'swa_count': swa.swa_count,
            }, swa_path)

    writer.close()
    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Best F1: {best_f1:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
