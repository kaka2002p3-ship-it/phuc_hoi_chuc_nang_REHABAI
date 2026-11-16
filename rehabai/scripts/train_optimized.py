"""
Optimized training script with advanced augmentation, focal loss with class weights,
and multi-seed support.

Features:
- Advanced data augmentation
- Focal loss with class weights
- Label smoothing
- Multi-seed training for ensemble
- Comprehensive logging
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
import random
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.device import select_training_device
from training.datasets.rehab_dataset import RehabDataset
from training.models.rehab_motionnet import RehabMotionNet
from training.augmentation import AdvancedAugmentation
from training.losses.class_weighted_loss import (
    FocalLoss,
    compute_class_weights,
    DynamicLossWeighting,
)
from training.inference.tta_inference import TTAEnsemble
from shared.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    detailed_evaluation,
    confusion_matrix,
)


def set_seed(seed: int):
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def compute_class_weights_from_dataset(dataset: RehabDataset, num_classes: int) -> torch.Tensor:
    """Compute balanced class weights from dataset."""
    labels = []
    for i in range(len(dataset)):
        item = dataset[i]
        if 'exercise' in item:
            labels.append(item['exercise'].item() if hasattr(item['exercise'], 'item') else item['exercise'])
        elif 'label' in item:
            labels.append(item['label'])

    return compute_class_weights(labels, num_classes, method='balanced')


def train_one_epoch(
    model,
    dataloader,
    criterion,
    optimizer,
    scaler,
    device,
    epoch: int,
    class_weights: torch.Tensor = None,
) -> dict:
    """Train for one epoch with advanced metrics."""
    model.train()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    all_probs = []

    pbar = tqdm(dataloader, desc=f"Epoch {epoch} [Train]")

    for batch in pbar:
        features = batch['features'].to(device)
        labels = batch['exercise'].to(device)

        optimizer.zero_grad()

        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            outputs = model(features)

            # If multi-task, use only exercise head output
            if isinstance(outputs, tuple):
                outputs = outputs[0]

            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()

        probs = torch.softmax(outputs, dim=-1)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()

        all_preds.extend(preds)
        all_labels.extend(labels.cpu().numpy())
        all_probs.extend(probs.detach().cpu().numpy())

        pbar.set_postfix({"loss": f"{loss.item():.4f}"})

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


def validate(
    model,
    dataloader,
    criterion,
    device,
    epoch: int,
) -> dict:
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc=f"Epoch {epoch} [Val]"):
            features = batch['features'].to(device)
            labels = batch['exercise'].to(device)

            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                outputs = model(features)

                if isinstance(outputs, tuple):
                    outputs = outputs[0]

                loss = criterion(outputs, labels)

            running_loss += loss.item()

            probs = torch.softmax(outputs, dim=-1)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()

            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    epoch_loss = running_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)

    # Detailed evaluation
    detailed = detailed_evaluation(all_labels, all_preds)

    return {
        'loss': epoch_loss,
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
        'predictions': all_preds,
        'labels': all_labels,
        'probabilities': np.array(all_probs),
        'detailed': detailed,
    }


def train_with_advanced_features(
    data_dir: str,
    train_manifest: str,
    val_manifest: str,
    norm_json: str,
    fold_id: str,
    source_dir: str,
    num_classes: int = 4,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 1e-3,
    seed: int = 42,
    # Augmentation params
    use_augmentation: bool = True,
    augmentation_scale_range: tuple = (0.8, 1.2),
    augmentation_noise_sigma: float = 0.01,
    augmentation_mask_ratio: float = 0.15,
    # Loss params
    use_focal_loss: bool = True,
    focal_gamma: float = 2.0,
    use_label_smoothing: bool = True,
    label_smoothing: float = 0.1,
    use_class_weights: bool = True,
    # Model params
    use_hand: bool = True,
    use_kinematic: bool = True,
    use_contrastive: bool = False,
    use_mstcn: bool = True,
    use_attention: bool = False,
    upper_limb_only: bool = True,
    # Output
    output_dir: str = "experiments/optimized_v1",
):
    """Main training function with advanced features."""

    # Set seed
    set_seed(seed)

    # Setup device
    device = select_training_device()
    print(f"\n{'='*60}")
    print(f"Training Configuration:")
    print(f"  Device: {device}")
    print(f"  Seed: {seed}")
    print(f"  Fold: {fold_id}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Learning Rate: {lr}")
    print(f"{'='*60}\n")

    # Create output directories
    output_path = Path(output_dir)
    fold_dir = output_path / f"fold_{fold_id}"
    fold_dir.mkdir(parents=True, exist_ok=True)

    checkpoints_dir = fold_dir / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)

    logs_dir = fold_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create datasets
    train_dataset = RehabDataset(
        data_dir=data_dir,
        source_dir=source_dir,
        split_manifest_csv=train_manifest,
        split='train',
        normalization_json=norm_json,
        fold_id=fold_id,
        apply_augmentation=use_augmentation,
    )

    val_dataset = RehabDataset(
        data_dir=data_dir,
        source_dir=source_dir,
        split_manifest_csv=val_manifest,
        split='val',
        normalization_json=norm_json,
        fold_id=fold_id,
        apply_augmentation=False,
    )

    print(f"Train size: {len(train_dataset)}, Val size: {len(val_dataset)}")

    # Compute class weights
    if use_class_weights:
        class_weights = compute_class_weights_from_dataset(train_dataset, num_classes)
        print(f"Class weights: {class_weights.tolist()}")
    else:
        class_weights = None

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=min(4, os.cpu_count() or 1),
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=min(4, os.cpu_count() or 1),
        pin_memory=True,
    )

    # Create model
    model = RehabMotionNet(
        num_exercises=num_classes,
        use_hand=use_hand,
        use_kinematic=use_kinematic,
        use_contrastive=use_contrastive,
        use_mstcn=use_mstcn,
        use_attention=use_attention,
        upper_limb_only=upper_limb_only,
    ).to(device)

    # Verify model is on CUDA
    assert next(model.parameters()).is_cuda, "Model not on CUDA!"

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Create loss function
    if use_focal_loss:
        criterion = FocalLoss(
            alpha=class_weights,
            gamma=focal_gamma,
            label_smoothing=label_smoothing if use_label_smoothing else 0.0,
        )
    else:
        criterion = torch.nn.CrossEntropyLoss(
            weight=class_weights,
            label_smoothing=label_smoothing if use_label_smoothing else 0.0,
        )

    # Create optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=1e-4,
    )

    # Create scheduler
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer,
        T_0=10,
        T_mult=2,
    )

    # Create GradScaler for mixed precision
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == 'cuda')

    # Setup TensorBoard
    writer = SummaryWriter(log_dir=str(logs_dir))

    # Training loop
    best_val_f1 = 0.0
    best_epoch = 0
    patience = 12
    patience_counter = 0
    training_history = []

    print(f"\nStarting training for {epochs} epochs...\n")

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()

        # Train
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch, class_weights
        )

        # Validate
        val_metrics = validate(model, val_loader, criterion, device, epoch)

        # Update scheduler
        scheduler.step()

        # Calculate epoch time
        epoch_time = time.time() - epoch_start

        # Log to TensorBoard
        writer.add_scalar('Loss/train', train_metrics['loss'], epoch)
        writer.add_scalar('Loss/val', val_metrics['loss'], epoch)
        writer.add_scalar('Accuracy/train', train_metrics['accuracy'], epoch)
        writer.add_scalar('Accuracy/val', val_metrics['accuracy'], epoch)
        writer.add_scalar('F1/train', train_metrics['f1'], epoch)
        writer.add_scalar('F1/val', val_metrics['f1'], epoch)
        writer.add_scalar('LR', optimizer.param_groups[0]['lr'], epoch)

        # Log per-class metrics
        if 'detailed' in val_metrics:
            for class_name, class_metrics in val_metrics['detailed']['per_class'].items():
                writer.add_scalar(f'PerClass/F1_{class_name}', class_metrics['f1_score'], epoch)

        # Print epoch summary
        print(f"\nEpoch {epoch}/{epochs} ({epoch_time:.1f}s)")
        print(f"  Train - Loss: {train_metrics['loss']:.4f}, Acc: {train_metrics['accuracy']:.4f}, F1: {train_metrics['f1']:.4f}")
        print(f"  Val   - Loss: {val_metrics['loss']:.4f}, Acc: {val_metrics['accuracy']:.4f}, F1: {val_metrics['f1']:.4f}")

        # Save epoch history
        epoch_record = {
            'epoch': epoch,
            'train_loss': train_metrics['loss'],
            'train_accuracy': train_metrics['accuracy'],
            'train_f1': train_metrics['f1'],
            'val_loss': val_metrics['loss'],
            'val_accuracy': val_metrics['accuracy'],
            'val_f1': val_metrics['f1'],
            'epoch_time': epoch_time,
            'lr': optimizer.param_groups[0]['lr'],
        }
        training_history.append(epoch_record)

        # Check for improvement
        if val_metrics['f1'] > best_val_f1:
            best_val_f1 = val_metrics['f1']
            best_epoch = epoch
            patience_counter = 0

            # Save best model
            best_model_path = checkpoints_dir / "best_model.pth"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_metrics['f1'],
                'val_accuracy': val_metrics['accuracy'],
                'val_loss': val_metrics['loss'],
                'config': {
                    'seed': seed,
                    'fold_id': fold_id,
                    'num_classes': num_classes,
                    'use_hand': use_hand,
                    'use_kinematic': use_kinematic,
                    'use_contrastive': use_contrastive,
                    'use_mstcn': use_mstcn,
                    'use_attention': use_attention,
                    'upper_limb_only': upper_limb_only,
                    'focal_gamma': focal_gamma,
                    'label_smoothing': label_smoothing,
                    'use_class_weights': use_class_weights,
                }
            }, best_model_path)
            print(f"  ✓ Saved best model (F1: {best_val_f1:.4f})")
        else:
            patience_counter += 1
            print(f"  No improvement ({patience_counter}/{patience})")

        # Early stopping
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch}")
            break

        print()

    # Save training history
    history_path = fold_dir / "training_history.json"
    with open(history_path, 'w') as f:
        json.dump({
            'config': {
                'seed': seed,
                'fold_id': fold_id,
                'epochs': epochs,
                'batch_size': batch_size,
                'lr': lr,
                'use_augmentation': use_augmentation,
                'use_focal_loss': use_focal_loss,
                'focal_gamma': focal_gamma,
                'label_smoothing': label_smoothing,
                'use_class_weights': use_class_weights,
            },
            'best_epoch': best_epoch,
            'best_val_f1': best_val_f1,
            'history': training_history,
        }, f, indent=2)

    # Final evaluation with TTA
    print("\n" + "="*60)
    print("Final Evaluation")
    print("="*60)

    final_val_metrics = validate(model, val_loader, criterion, device, best_epoch)
    print(f"Best Epoch: {best_epoch}")
    print(f"Best Val F1: {best_val_f1:.4f}")
    print(f"Best Val Accuracy: {final_val_metrics['accuracy']:.4f}")

    if 'detailed' in final_val_metrics:
        print("\nPer-class F1:")
        for class_name, metrics in final_val_metrics['detailed']['per_class'].items():
            print(f"  {class_name}: {metrics['f1_score']:.4f} (support: {metrics['support']})")

    writer.close()

    print(f"\nTraining complete!")
    print(f"Best model saved to: {best_model_path}")
    print(f"Training history saved to: {history_path}")

    return {
        'best_epoch': best_epoch,
        'best_val_f1': best_val_f1,
        'best_val_accuracy': final_val_metrics['accuracy'],
        'training_history': training_history,
    }


def main():
    parser = argparse.ArgumentParser(description="Optimized training for RehabAI")

    # Data arguments
    parser.add_argument("--data_dir", type=str, default="data/stage3_upper_limb/processed/keypoints",
                        help="Path to processed keypoints data")
    parser.add_argument("--train_manifest", type=str, required=True,
                        help="Path to training manifest CSV")
    parser.add_argument("--val_manifest", type=str, required=True,
                        help="Path to validation manifest CSV")
    parser.add_argument("--norm_json", type=str, required=True,
                        help="Path to normalization JSON")
    parser.add_argument("--source_dir", type=str, required=True,
                        help="Path to source video directory")
    parser.add_argument("--fold_id", type=str, required=True,
                        help="Fold identifier (e.g., '01', '02', etc.)")

    # Training arguments
    parser.add_argument("--epochs", type=int, default=30,
                        help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=32,
                        help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3,
                        help="Learning rate")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--num_classes", type=int, default=4,
                        help="Number of exercise classes")

    # Augmentation arguments
    parser.add_argument("--no_augmentation", action="store_true",
                        help="Disable data augmentation")
    parser.add_argument("--aug_scale_min", type=float, default=0.8,
                        help="Minimum scale for augmentation")
    parser.add_argument("--aug_scale_max", type=float, default=1.2,
                        help="Maximum scale for augmentation")
    parser.add_argument("--aug_noise_sigma", type=float, default=0.01,
                        help="Noise sigma for augmentation")
    parser.add_argument("--aug_mask_ratio", type=float, default=0.15,
                        help="Mask ratio for augmentation")

    # Loss arguments
    parser.add_argument("--no_focal_loss", action="store_true",
                        help="Use standard cross entropy instead of focal loss")
    parser.add_argument("--focal_gamma", type=float, default=2.0,
                        help="Focal loss gamma parameter")
    parser.add_argument("--no_label_smoothing", action="store_true",
                        help="Disable label smoothing")
    parser.add_argument("--label_smoothing", type=float, default=0.1,
                        help="Label smoothing factor")
    parser.add_argument("--no_class_weights", action="store_true",
                        help="Disable class weights")

    # Model arguments
    parser.add_argument("--no_hand", action="store_true",
                        help="Disable hand branch")
    parser.add_argument("--no_kinematic", action="store_true",
                        help="Disable kinematic branch")
    parser.add_argument("--use_contrastive", action="store_true",
                        help="Use contrastive pretrained encoder")
    parser.add_argument("--no_mstcn", action="store_true",
                        help="Disable MS-TCN")
    parser.add_argument("--use_attention", action="store_true",
                        help="Use attention mechanism")

    # Output arguments
    parser.add_argument("--output_dir", type=str, default="experiments/optimized_v1",
                        help="Output directory for checkpoints and logs")

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.train_manifest):
        raise FileNotFoundError(f"Train manifest not found: {args.train_manifest}")
    if not os.path.exists(args.val_manifest):
        raise FileNotFoundError(f"Val manifest not found: {args.val_manifest}")
    if not os.path.exists(args.norm_json):
        raise FileNotFoundError(f"Normalization JSON not found: {args.norm_json}")

    # Train
    train_with_advanced_features(
        data_dir=args.data_dir,
        train_manifest=args.train_manifest,
        val_manifest=args.val_manifest,
        norm_json=args.norm_json,
        fold_id=args.fold_id,
        source_dir=args.source_dir,
        num_classes=args.num_classes,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seed=args.seed,
        # Augmentation
        use_augmentation=not args.no_augmentation,
        augmentation_scale_range=(args.aug_scale_min, args.aug_scale_max),
        augmentation_noise_sigma=args.aug_noise_sigma,
        augmentation_mask_ratio=args.aug_mask_ratio,
        # Loss
        use_focal_loss=not args.no_focal_loss,
        focal_gamma=args.focal_gamma,
        use_label_smoothing=not args.no_label_smoothing,
        label_smoothing=args.label_smoothing,
        use_class_weights=not args.no_class_weights,
        # Model
        use_hand=not args.no_hand,
        use_kinematic=not args.no_kinematic,
        use_contrastive=args.use_contrastive,
        use_mstcn=not args.no_mstcn,
        use_attention=args.use_attention,
        upper_limb_only=True,
        # Output
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
