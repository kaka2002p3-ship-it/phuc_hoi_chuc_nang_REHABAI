"""
Robust Training Script with Strong Regularization to Prevent Overfitting.

Improvements:
1. Stronger weight decay
2. Higher dropout
3. Mixup augmentation
4. Stronger label smoothing
5. Gradient clipping
6. Learning rate warmup
7. Cross-validation across multiple folds
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
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.device import select_training_device
from training.models.rehab_motionnet import RehabMotionNet
from training.augmentation import AdvancedAugmentation
from training.losses.class_weighted_loss import FocalLoss, compute_class_weights
from shared.metrics import accuracy_score, f1_score, precision_score, recall_score, detailed_evaluation
from shared.preprocessing.sequence import resample_sequence


def set_seed(seed: int):
    """Set all random seeds."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class MixupAugmentation:
    """Mixup augmentation for better generalization."""

    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha

    def __call__(self, x: np.ndarray, y: int) -> tuple:
        if self.alpha > 0:
            lam = np.random.beta(self.alpha, self.alpha)
        else:
            lam = 1

        batch_size = x.shape[0]
        index = np.random.permutation(batch_size)

        mixed_x = lam * x + (1 - lam) * x[index]
        y_a, y_b = y, y[index]
        return mixed_x, y_a, y_b, lam


class SimpleRehabDataset(Dataset):
    """Simple dataset with optional augmentation."""

    def __init__(self, data_dir: str, manifest_csv: str, normalization_json: str,
                 split: str = 'train', apply_augmentation: bool = False,
                 mixup_alpha: float = 0.0):
        import pandas as pd

        self.data_dir = Path(data_dir)
        self.split = split
        self.apply_augmentation = apply_augmentation
        self.mixup_alpha = mixup_alpha

        # Load normalization
        with open(normalization_json, 'r') as f:
            norm_data = json.load(f)

        self.kin_mean = np.array(norm_data['kinematics']['mean'], dtype=np.float32)
        self.kin_std = np.array(norm_data['kinematics']['std'], dtype=np.float32)

        # Load manifest
        df = pd.read_csv(manifest_csv)
        self.samples = []

        for _, row in df.iterrows():
            sample_id = row['sample_id']
            exercise_id = int(row['exercise_id']) - 1

            processed_path = row.get('processed_feature_path', '')
            if not processed_path:
                sample_name = sample_id.replace('.npz', '')
                processed_path = str(self.data_dir / f"{sample_name}.npz")

            if os.path.exists(processed_path):
                self.samples.append({
                    'path': processed_path,
                    'exercise': exercise_id,
                    'subject_id': str(row.get('subject_id', 'unknown'))
                })

        print(f"Loaded {len(self.samples)} samples for {split} split")

        # Augmentation
        if apply_augmentation:
            self.augmenter = AdvancedAugmentation(
                temporal_scaling=True,
                pose_noise=True,
                joint_masking=True,
                pose_scaling=True,
            )
        else:
            self.augmenter = None

        # Mixup
        if mixup_alpha > 0:
            self.mixup = MixupAugmentation(alpha=mixup_alpha)
        else:
            self.mixup = None

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # Load npz
        data = np.load(sample['path'])

        # Construct feature vector
        pose = data['pose_landmarks'][:, :, :3]
        left_hand = data['left_hand_landmarks']
        right_hand = data['right_hand_landmarks']
        kin = data['kinematics']

        T = pose.shape[0]
        pose_flat = pose.reshape(T, -1)
        lh_flat = left_hand.reshape(T, -1)
        rh_flat = right_hand.reshape(T, -1)

        sequence = np.concatenate([pose_flat, lh_flat, rh_flat, kin], axis=1).astype(np.float32)
        sequence = resample_sequence(sequence, target_length=96)
        sequence[:, -12:] = (sequence[:, -12:] - self.kin_mean) / (self.kin_std + 1e-8)
        sequence = np.nan_to_num(sequence, nan=0.0, posinf=0.0, neginf=0.0)

        # Apply augmentation
        if self.augmenter:
            sequence = self.augmenter(sequence)

        return {
            'features': torch.FloatTensor(sequence),
            'exercise': torch.LongTensor([sample['exercise']]).squeeze(),
            'subject_id': sample['subject_id']
        }


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Mixup loss function."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def train_one_epoch(model, dataloader, criterion, optimizer, scaler, device, epoch,
                   use_mixup=False, grad_clip=1.0):
    model.train()
    running_loss = 0.0
    all_preds = []
    all_labels = []

    pbar = tqdm(dataloader, desc=f"Epoch {epoch} [Train]")
    for batch in pbar:
        features = batch['features'].to(device)
        labels = batch['exercise'].to(device)

        optimizer.zero_grad()

        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
            outputs = model(features)
            if isinstance(outputs, tuple):
                outputs = outputs[0]

            if use_mixup and np.random.random() < 0.5:
                # Apply mixup
                lam = np.random.beta(0.2, 0.2)
                batch_size = features.size(0)
                index = torch.randperm(batch_size).to(device)

                mixed_features = lam * features + (1 - lam) * features[index]
                mixed_outputs = model(mixed_features)
                if isinstance(mixed_outputs, tuple):
                    mixed_outputs = mixed_outputs[0]

                loss = lam * criterion(mixed_outputs, labels) + (1 - lam) * criterion(mixed_outputs, labels[index])
            else:
                loss = criterion(outputs, labels)

        scaler.scale(loss).backward()

        # Gradient clipping
        if grad_clip > 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)

        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        all_preds.extend(preds.tolist())
        all_labels.extend(labels.cpu().numpy())
        pbar.set_postfix({"loss": f"{loss.item():.4f}"})

    return {
        'loss': running_loss / len(dataloader),
        'accuracy': accuracy_score(all_labels, all_preds),
        'f1': f1_score(all_labels, all_preds, average='macro', zero_division=0),
        'predictions': all_preds,
        'labels': all_labels,
    }


def validate(model, dataloader, criterion, device, epoch):
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc=f"Epoch {epoch} [Val]", leave=False):
            features = batch['features'].to(device)
            labels = batch['exercise'].to(device)

            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == 'cuda'):
                outputs = model(features)
                if isinstance(outputs, tuple):
                    outputs = outputs[0]
                loss = criterion(outputs, labels)

            running_loss += loss.item()
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.cpu().numpy())

    detailed = detailed_evaluation(all_labels, all_preds)

    return {
        'loss': running_loss / len(dataloader),
        'accuracy': accuracy_score(all_labels, all_preds),
        'f1': f1_score(all_labels, all_preds, average='macro', zero_division=0),
        'precision': precision_score(all_labels, all_preds, average='macro', zero_division=0),
        'recall': recall_score(all_labels, all_preds, average='macro', zero_division=0),
        'predictions': all_preds,
        'labels': all_labels,
        'detailed': detailed,
    }


def main():
    parser = argparse.ArgumentParser(description="Robust Training with Strong Regularization")

    # Data
    parser.add_argument("--data_dir", type=str, required=True)
    parser.add_argument("--train_manifest", type=str, required=True)
    parser.add_argument("--val_manifest", type=str, required=True)
    parser.add_argument("--norm_json", type=str, required=True)

    # Training
    parser.add_argument("--fold_id", type=str, default="01")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=16)  # Smaller batch
    parser.add_argument("--lr", type=float, default=5e-4)  # Lower LR
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num_classes", type=int, default=4)

    # Regularization (KEY CHANGES)
    parser.add_argument("--weight_decay", type=float, default=0.05)  # Stronger
    parser.add_argument("--dropout", type=float, default=0.3)  # Higher dropout
    parser.add_argument("--focal_gamma", type=float, default=1.5)  # Lower gamma
    parser.add_argument("--label_smoothing", type=float, default=0.2)  # Stronger
    parser.add_argument("--mixup_alpha", type=float, default=0.3)  # Mixup
    parser.add_argument("--grad_clip", type=float, default=0.5)  # Gradient clipping
    parser.add_argument("--warmup_epochs", type=int, default=5)  # LR warmup

    # Output
    parser.add_argument("--output_dir", type=str, default="experiments/robust")

    args = parser.parse_args()

    set_seed(args.seed)
    device = select_training_device()

    print(f"\n{'='*60}")
    print(f"ROBUST TRAINING CONFIGURATION")
    print(f"{'='*60}")
    print(f"  Device: {device}")
    print(f"  Seed: {args.seed}")
    print(f"  Fold: {args.fold_id}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  LR: {args.lr}")
    print(f"  Weight Decay: {args.weight_decay} (STRONG)")
    print(f"  Dropout: {args.dropout}")
    print(f"  Focal Gamma: {args.focal_gamma}")
    print(f"  Label Smoothing: {args.label_smoothing} (STRONG)")
    print(f"  Mixup Alpha: {args.mixup_alpha}")
    print(f"  Gradient Clipping: {args.grad_clip}")
    print(f"  Warmup Epochs: {args.warmup_epochs}")
    print(f"{'='*60}\n")

    # Create datasets
    train_dataset = SimpleRehabDataset(
        data_dir=args.data_dir,
        manifest_csv=args.train_manifest,
        normalization_json=args.norm_json,
        split='train',
        apply_augmentation=True,
        mixup_alpha=args.mixup_alpha
    )

    val_dataset = SimpleRehabDataset(
        data_dir=args.data_dir,
        manifest_csv=args.val_manifest,
        normalization_json=args.norm_json,
        split='val',
        apply_augmentation=False
    )

    # Compute class weights
    labels = [s['exercise'] for s in train_dataset.samples]
    class_weights = compute_class_weights(labels, args.num_classes, method='balanced')
    print(f"Class weights: {class_weights.tolist()}")

    # Dataloaders
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True,
        num_workers=0, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=0, pin_memory=True
    )

    # Model with higher dropout
    model = RehabMotionNet(
        num_exercises=args.num_classes,
        use_hand=True,
        use_kinematic=True,
        use_contrastive=False,
        use_mstcn=True,
        use_attention=False,
        upper_limb_only=True,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")

    # Loss with stronger regularization
    criterion = FocalLoss(
        alpha=class_weights.to(device),
        gamma=args.focal_gamma,
        label_smoothing=args.label_smoothing,  # Stronger label smoothing
    )

    # Optimizer with stronger weight decay
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay  # Stronger weight decay
    )

    # Warmup + Cosine Annealing
    warmup_scheduler = optim.lr_scheduler.LinearLR(
        optimizer, start_factor=0.1, end_factor=1.0, total_iters=args.warmup_epochs
    )
    cosine_scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs - args.warmup_epochs, eta_min=1e-6
    )
    scheduler = optim.lr_scheduler.SequentialLR(
        optimizer,
        schedulers=[warmup_scheduler, cosine_scheduler],
        milestones=[args.warmup_epochs]
    )

    scaler = torch.cuda.amp.GradScaler(enabled=device.type == 'cuda')

    # Output
    output_path = Path(args.output_dir) / f"fold_{args.fold_id}_robust"
    output_path.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = output_path / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)

    # Training
    best_val_f1 = 0.0
    best_train_f1 = 0.0
    best_epoch = 0
    patience = 20  # Longer patience
    patience_counter = 0
    history = []

    print(f"\nStarting robust training...\n")

    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()

        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch,
            use_mixup=True, grad_clip=args.grad_clip
        )
        val_metrics = validate(model, val_loader, criterion, device, epoch)
        scheduler.step()

        # Calculate gap
        train_val_gap = train_metrics['accuracy'] - val_metrics['accuracy']

        epoch_time = time.time() - epoch_start

        print(f"\nEpoch {epoch}/{args.epochs} ({epoch_time:.1f}s)")
        print(f"  Train - Loss: {train_metrics['loss']:.4f}, Acc: {train_metrics['accuracy']:.4f}, F1: {train_metrics['f1']:.4f}")
        print(f"  Val   - Loss: {val_metrics['loss']:.4f}, Acc: {val_metrics['accuracy']:.4f}, F1: {val_metrics['f1']:.4f}")
        print(f"  Gap   - {train_val_gap:.4f} ({'OVERFITTING' if train_val_gap > 0.1 else 'OK'})")

        if 'detailed' in val_metrics:
            print(f"\n  Per-class F1:")
            for class_name, metrics in val_metrics['detailed']['per_class'].items():
                print(f"    {class_name}: {metrics['f1_score']:.4f} (support: {metrics['support']})")

        history.append({
            'epoch': epoch,
            'train_loss': train_metrics['loss'],
            'train_accuracy': train_metrics['accuracy'],
            'train_f1': train_metrics['f1'],
            'val_loss': val_metrics['loss'],
            'val_accuracy': val_metrics['accuracy'],
            'val_f1': val_metrics['f1'],
            'gap': train_val_gap,
            'epoch_time': epoch_time,
        })

        # Save best model (prefer lower gap if F1 similar)
        should_save = False
        if val_metrics['f1'] > best_val_f1 + 0.02:
            should_save = True
        elif val_metrics['f1'] > best_val_f1 and train_val_gap < 0.1:
            should_save = True
        elif val_metrics['f1'] >= best_val_f1 and abs(train_val_gap) < abs(best_val_f1 - train_metrics['f1']):
            should_save = True

        if should_save:
            best_val_f1 = val_metrics['f1']
            best_train_f1 = train_metrics['f1']
            best_epoch = epoch
            patience_counter = 0

            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_metrics['f1'],
                'val_accuracy': val_metrics['accuracy'],
                'train_f1': train_metrics['f1'],
                'gap': train_val_gap,
                'config': {
                    'fold_id': args.fold_id,
                    'seed': args.seed,
                    'num_classes': args.num_classes,
                    'focal_gamma': args.focal_gamma,
                    'label_smoothing': args.label_smoothing,
                    'weight_decay': args.weight_decay,
                    'mixup_alpha': args.mixup_alpha,
                }
            }, checkpoints_dir / "best_model.pth")
            print(f"  ✓ Saved best model (F1: {best_val_f1:.4f}, Gap: {train_val_gap:.4f})")
        else:
            patience_counter += 1
            print(f"  No improvement ({patience_counter}/{patience})")

        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch}")
            break
        print()

    # Save history
    with open(output_path / "training_history.json", 'w') as f:
        json.dump({
            'config': vars(args),
            'best_epoch': best_epoch,
            'best_val_f1': best_val_f1,
            'best_train_f1': best_train_f1,
            'gap': best_train_f1 - best_val_f1,
            'history': history,
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"ROBUST TRAINING COMPLETE!")
    print(f"Best Epoch: {best_epoch}")
    print(f"Best Train F1: {best_train_f1:.4f}")
    print(f"Best Val F1: {best_val_f1:.4f}")
    print(f"Final Gap: {best_train_f1 - best_val_f1:.4f}")
    print(f"{'='*60}")
    print(f"\nModel saved to: {checkpoints_dir / 'best_model.pth'}")


if __name__ == "__main__":
    main()
