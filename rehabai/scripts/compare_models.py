"""Evaluate robust model on all folds."""
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
    return model, checkpoint


def evaluate_fold(fold_id, model, device):
    test_manifest = f"data/stage3_upper_limb/loso/{fold_id}/test_manifest.csv"
    norm_json = f"data/stage3_upper_limb/loso/{fold_id}/normalization.json"
    data_dir = "data/stage3_upper_limb/processed/keypoints"

    if not Path(test_manifest).exists():
        return None

    try:
        dataset = SimpleRehabDataset(
            data_dir=data_dir,
            manifest_csv=test_manifest,
            normalization_json=norm_json,
            split='test',
            apply_augmentation=False
        )
    except:
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

    return {
        'fold': fold_id,
        'samples': len(dataset),
        'accuracy': acc,
        'f1': f1,
    }


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    # Load models
    models = [
        ("experiments/optimized_seed7/fold_04_seed7/checkpoints/best_model.pth", "Original (Seed 7)"),
        ("experiments/robust_v1/fold_04_robust/checkpoints/best_model.pth", "Robust (Reg)"),
    ]

    all_results = {}

    for model_path, model_name in models:
        if not Path(model_path).exists():
            print(f"Model not found: {model_path}")
            continue

        print(f"\n{'='*60}")
        print(f"Evaluating: {model_name}")
        print(f"{'='*60}")

        model, checkpoint = load_model(model_path, device)
        print(f"Best Epoch: {checkpoint.get('epoch', 'N/A')}")
        print(f"Val F1: {checkpoint.get('val_f1', 0):.4f}")
        gap = checkpoint.get('gap', 0)
        print(f"Gap: {gap if isinstance(gap, (int, float)) else 'N/A'}")

        results = []
        for fold in range(1, 11):
            fold_id = f"fold_{fold:02d}"
            result = evaluate_fold(fold_id, model, device)
            if result:
                print(f"  {fold_id}: Acc={result['accuracy']:.4f}, F1={result['f1']:.4f} ({result['samples']} samples)")
                results.append(result)

        if results:
            mean_acc = np.mean([r['accuracy'] for r in results])
            std_acc = np.std([r['accuracy'] for r in results])
            mean_f1 = np.mean([r['f1'] for r in results])
            std_f1 = np.std([r['f1'] for r in results])

            print(f"\n  Mean Accuracy: {mean_acc:.4f} ± {std_acc:.4f}")
            print(f"  Mean F1:       {mean_f1:.4f} ± {std_f1:.4f}")

            all_results[model_name] = {
                'mean_accuracy': mean_acc,
                'std_accuracy': std_acc,
                'mean_f1': mean_f1,
                'std_f1': std_f1,
                'results': results,
            }

    # Comparison
    if len(all_results) >= 2:
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        print(f"\n{'Model':<20} {'Accuracy':<15} {'F1 Score':<15}")
        print("-" * 50)
        for name, data in all_results.items():
            print(f"{name:<20} {data['mean_accuracy']:.4f}±{data['std_accuracy']:.4f}     {data['mean_f1']:.4f}±{data['std_f1']:.4f}")

    # Save
    import json
    with open('experiments/comparison_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to: experiments/comparison_results.json")


if __name__ == "__main__":
    main()
