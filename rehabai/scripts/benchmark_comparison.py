"""
Benchmark comparison: Baseline vs Optimized Models
"""

from __future__ import annotations

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.device import select_training_device
from training.models.rehab_motionnet import RehabMotionNet
from training.losses.class_weighted_loss import FocalLoss, compute_class_weights
from scripts.train_simple import SimpleRehabDataset, set_seed, validate
from torch.utils.data import DataLoader
import torch


def load_model(checkpoint_path: str, device, num_classes=4):
    """Load a trained model from checkpoint."""
    model = RehabMotionNet(
        num_exercises=num_classes,
        use_hand=True,
        use_kinematic=True,
        use_contrastive=False,
        use_mstcn=True,
        use_attention=False,
        upper_limb_only=True,
    ).to(device)

    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model, checkpoint.get('config', {})


def benchmark_model(model, val_loader, criterion, device, model_name):
    """Benchmark a single model."""
    print(f"\n{'='*50}")
    print(f"Benchmarking: {model_name}")
    print(f"{'='*50}")

    results = validate(model, val_loader, criterion, device, epoch=0)

    print(f"Accuracy: {results['accuracy']:.4f}")
    print(f"F1 Score: {results['f1']:.4f}")
    print(f"Precision: {results['precision']:.4f}")
    print(f"Recall: {results['recall']:.4f}")

    if 'detailed' in results:
        print(f"\nPer-class F1:")
        for class_name, metrics in results['detailed']['per_class'].items():
            print(f"  {class_name}: {metrics['f1_score']:.4f} (support: {metrics['support']})")

    return {
        'name': model_name,
        'accuracy': results['accuracy'],
        'f1': results['f1'],
        'precision': results['precision'],
        'recall': results['recall'],
        'detailed': results.get('detailed', {}),
    }


def main():
    device = select_training_device()
    print(f"Using device: {device}")

    # Load validation data
    val_dataset = SimpleRehabDataset(
        data_dir="data/stage3_upper_limb/processed/keypoints",
        manifest_csv="data/stage3_upper_limb/loso/fold_04/val_manifest.csv",
        normalization_json="data/stage3_upper_limb/loso/fold_04/normalization.json",
        split='val',
        apply_augmentation=False
    )

    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=0)

    # Compute class weights for loss
    labels = [s['exercise'] for s in val_dataset.samples]
    class_weights = compute_class_weights(labels, 4, method='balanced')
    criterion = FocalLoss(alpha=class_weights.to(device), gamma=2.0, label_smoothing=0.1)

    results = []

    # 1. Baseline model (original v2)
    print("\n" + "="*70)
    print("BASELINE MODEL (Original v2)")
    print("="*70)

    try:
        baseline_result = benchmark_model(
            None, val_loader, criterion, device,
            "Baseline (Original v2)"
        )
        baseline_result['note'] = "From artifacts/model_v2/"
        results.append(baseline_result)
    except Exception as e:
        print(f"Could not load baseline: {e}")

    # 2. Optimized models (each seed)
    seed_results = []
    seeds = [
        ("experiments/optimized_v1/fold_04/checkpoints/best_model_seed42.pth", "Optimized Seed 42"),
        ("experiments/optimized_seed7/fold_04_seed7/checkpoints/best_model.pth", "Optimized Seed 7"),
        ("experiments/optimized_seed2026/fold_04/checkpoints/best_model.pth", "Optimized Seed 2026"),
        ("experiments/optimized_seed123/fold_04/checkpoints/best_model.pth", "Optimized Seed 123"),
    ]

    for checkpoint_path, name in seeds:
        if Path(checkpoint_path).exists():
            try:
                model, config = load_model(checkpoint_path, device)
                result = benchmark_model(model, val_loader, criterion, device, name)
                result['config'] = config
                seed_results.append(result)
            except Exception as e:
                print(f"Could not load {name}: {e}")
        else:
            print(f"Checkpoint not found: {checkpoint_path}")

    results.extend(seed_results)

    # 3. Ensemble (average of all seeds)
    if seed_results:
        print("\n" + "="*70)
        print("ENSEMBLE (Average of 4 seeds)")
        print("="*70)

        # Simple probability averaging ensemble
        all_preds = []
        all_labels = []

        from tqdm import tqdm
        with torch.no_grad():
            for batch in tqdm(val_loader, desc="Ensemble inference"):
                features = batch['features'].to(device)
                labels = batch['exercise'].to(device)

                probs_list = []
                for checkpoint_path, _ in seeds:
                    if Path(checkpoint_path).exists():
                        try:
                            model, _ = load_model(checkpoint_path, device)
                            outputs = model(features)
                            if isinstance(outputs, tuple):
                                outputs = outputs[0]
                            probs = torch.softmax(outputs.float(), dim=1)
                            probs_list.append(probs.cpu().numpy())
                        except:
                            pass

                if probs_list:
                    # Average probabilities
                    avg_probs = torch.FloatTensor(sum(probs_list) / len(probs_list))
                    preds = torch.argmax(avg_probs, dim=1).cpu().numpy()
                    all_preds.extend(preds.tolist())
                    all_labels.extend(labels.cpu().numpy().tolist())

        from shared.metrics import accuracy_score, f1_score, precision_score, recall_score, detailed_evaluation

        ensemble_accuracy = accuracy_score(all_labels, all_preds)
        ensemble_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
        ensemble_precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
        ensemble_recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)
        ensemble_detailed = detailed_evaluation(all_labels, all_preds)

        print(f"Ensemble Accuracy: {ensemble_accuracy:.4f}")
        print(f"Ensemble F1 Score: {ensemble_f1:.4f}")
        print(f"Ensemble Precision: {ensemble_precision:.4f}")
        print(f"Ensemble Recall: {ensemble_recall:.4f}")

        results.append({
            'name': 'Ensemble (4 seeds)',
            'accuracy': ensemble_accuracy,
            'f1': ensemble_f1,
            'precision': ensemble_precision,
            'recall': ensemble_recall,
            'detailed': ensemble_detailed,
        })

    # Summary
    print("\n" + "="*70)
    print("FINAL COMPARISON SUMMARY")
    print("="*70)
    print(f"\n{'Model':<30} {'Accuracy':<12} {'F1 Score':<12} {'Improvement':<15}")
    print("-"*70)

    baseline_f1 = results[0]['f1'] if results else 0

    for r in results:
        improvement = (r['f1'] - baseline_f1) * 100 if baseline_f1 > 0 else 0
        print(f"{r['name']:<30} {r['accuracy']:<12.4f} {r['f1']:<12.4f} {'+' + f'{improvement:.2f}%' if improvement >= 0 else f'{improvement:.2f}%':<15}")

    # Save results
    output = {
        'baseline_f1': baseline_f1,
        'results': results,
    }

    with open('experiments/benchmark_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to: experiments/benchmark_results.json")


if __name__ == "__main__":
    main()
