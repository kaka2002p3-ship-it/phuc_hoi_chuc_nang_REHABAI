"""
Evaluate model on ALL 10 folds for fair comparison.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import numpy as np
from tqdm import tqdm

from training.models.rehab_motionnet import RehabMotionNet
from scripts.train_simple import SimpleRehabDataset
from shared.metrics import accuracy_score, f1_score, detailed_evaluation


def load_model(checkpoint_path, device):
    model = RehabMotionNet(
        num_exercises=4,
        use_hand=True,
        use_kinematic=True,
        use_contrastive=False,
        use_mstcn=True,
        use_attention=False,
        upper_limb_only=True,
    ).to(device)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    return model


def evaluate_fold(fold_id, model, device):
    """Evaluate on a single fold."""
    test_manifest = f"data/stage3_upper_limb/loso/{fold_id}/test_manifest.csv"
    norm_json = f"data/stage3_upper_limb/loso/{fold_id}/normalization.json"
    data_dir = "data/stage3_upper_limb/processed/keypoints"

    if not Path(test_manifest).exists() or not Path(norm_json).exists():
        return None

    try:
        dataset = SimpleRehabDataset(
            data_dir=data_dir,
            manifest_csv=test_manifest,
            normalization_json=norm_json,
            split='test',
            apply_augmentation=False
        )
    except Exception as e:
        print(f"  Error loading {fold_id}: {e}")
        return None

    if len(dataset) == 0:
        return None

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for i in tqdm(range(len(dataset)), desc=f"  {fold_id}", leave=False):
            sample = dataset[i]
            features = sample['features'].unsqueeze(0).to(device)

            outputs = model(features)
            if isinstance(outputs, tuple):
                outputs = outputs[0]

            pred = torch.argmax(outputs, dim=1).item()
            all_preds.append(pred)
            all_labels.append(sample['exercise'].item())

    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    detailed = detailed_evaluation(all_labels, all_preds)

    return {
        'fold': fold_id,
        'samples': len(dataset),
        'accuracy': acc,
        'f1': f1,
        'detailed': detailed,
    }


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Load the best model (Seed 7)
    model_path = "experiments/optimized_seed7/fold_04_seed7/checkpoints/best_model.pth"
    print(f"\nLoading model from: {model_path}")
    model = load_model(model_path, device)

    # Evaluate on all 10 folds
    print("\nEvaluating on ALL 10 folds...")
    results = []

    for fold in range(1, 11):
        fold_id = f"fold_{fold:02d}"
        print(f"\nFold {fold_id}:")
        result = evaluate_fold(fold_id, model, device)
        if result:
            print(f"  Samples: {result['samples']}")
            print(f"  Accuracy: {result['accuracy']:.4f}")
            print(f"  F1 Score: {result['f1']:.4f}")
            results.append(result)
        else:
            print(f"  Skipped (missing data)")

    # Summary
    if results:
        print("\n" + "="*60)
        print("FINAL RESULTS (All 10 folds)")
        print("="*60)

        accuracies = [r['accuracy'] for r in results]
        f1_scores = [r['f1'] for r in results]

        print(f"\n{'Fold':<10} {'Samples':<10} {'Accuracy':<12} {'F1 Score':<12}")
        print("-"*44)
        for r in results:
            print(f"{r['fold']:<10} {r['samples']:<10} {r['accuracy']:<12.4f} {r['f1']:<12.4f}")

        print("-"*44)
        print(f"{'Mean':<10} {'':<10} {np.mean(accuracies):<12.4f} {np.mean(f1_scores):<12.4f}")
        print(f"{'Std':<10} {'':<10} {np.std(accuracies):<12.4f} {np.std(f1_scores):<12.4f}")

        print(f"\n\nComparison with Baseline:")
        print(f"  Baseline F1:  0.3544 ± 0.2704")
        print(f"  Optimized F1: {np.mean(f1_scores):.4f} ± {np.std(f1_scores):.4f}")
        print(f"  Improvement:   +{(np.mean(f1_scores) - 0.3544) * 100:.2f}%")

        # Save results
        import json
        with open('experiments/full_evaluation.json', 'w') as f:
            json.dump({
                'results': results,
                'mean_accuracy': float(np.mean(accuracies)),
                'std_accuracy': float(np.std(accuracies)),
                'mean_f1': float(np.mean(f1_scores)),
                'std_f1': float(np.std(f1_scores)),
            }, f, indent=2)
        print(f"\nResults saved to: experiments/full_evaluation.json")


if __name__ == "__main__":
    main()
