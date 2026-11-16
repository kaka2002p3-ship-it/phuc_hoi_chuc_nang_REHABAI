"""
Multi-seed ensemble evaluation script.

Trains models with multiple random seeds and evaluates ensemble performance.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.device import select_training_device
from training.datasets.rehab_dataset import RehabDataset
from training.models.rehab_motionnet import RehabMotionNet
from training.augmentation import AdvancedAugmentation
from training.losses.class_weighted_loss import FocalLoss, compute_class_weights
from training.inference.tta_inference import TTAEnsemble
from shared.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    detailed_evaluation,
    confusion_matrix,
)
from training.checkpoint_utils import compute_file_sha256


# Default seeds for ensemble
DEFAULT_SEEDS = [42, 7, 2026, 123, 456]


def set_seed(seed: int):
    """Set all random seeds."""
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_ensemble_models(
    checkpoint_dir: Path,
    seeds: list[int],
    fold_id: str,
    config: dict,
    device: torch.device,
) -> list[RehabMotionNet]:
    """Load multiple models from different seeds."""
    models = []

    for seed in seeds:
        checkpoint_path = checkpoint_dir / f"fold_{fold_id}" / f"model_seed_{seed}.pth"

        if not checkpoint_path.exists():
            print(f"Warning: Checkpoint not found for seed {seed}: {checkpoint_path}")
            continue

        model = RehabMotionNet(**config).to(device)
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        models.append(model)
        print(f"Loaded model from seed {seed}")

    return models


def ensemble_predict(
    models: list[RehabMotionNet],
    dataloader: DataLoader,
    device: torch.device,
    use_tta: bool = False,
) -> tuple[list[int], list[int], np.ndarray]:
    """
    Make predictions using ensemble of models.

    Returns:
        predictions, labels, all_probabilities
    """
    all_predictions = []
    all_labels = []
    all_probabilities = []

    tta_predictors = []
    if use_tta:
        for model in models:
            tta_predictors.append(TTAEnsemble(model, device=str(device), num_augmentations=5))

    for batch in tqdm(dataloader, desc="Ensemble inference"):
        features = batch['features'].to(device)
        labels = batch['exercise'].cpu().numpy()
        batch_probs = []

        for i, model in enumerate(models):
            with torch.no_grad():
                if use_tta and i < len(tta_predictors):
                    # Use TTA for this model
                    probs_list = []
                    for seq in features:
                        result = tta_predictors[i].predict(seq.cpu().numpy())
                        probs_list.append(result['probabilities'])
                    probs = torch.FloatTensor(probs_list)
                else:
                    outputs = model(features)
                    if isinstance(outputs, tuple):
                        outputs = outputs[0]
                    probs = torch.softmax(outputs.float(), dim=-1)

                batch_probs.append(probs.cpu().numpy())

        # Average probabilities across models
        avg_probs = np.mean(batch_probs, axis=0)
        predictions = np.argmax(avg_probs, axis=1)

        all_predictions.extend(predictions.tolist())
        all_labels.extend(labels.tolist())
        all_probabilities.append(avg_probs)

    all_probabilities = np.vstack(all_probabilities)

    return all_predictions, all_labels, all_probabilities


def evaluate_ensemble(
    checkpoint_dir: Path,
    data_dir: Path,
    val_manifest: Path,
    norm_json: Path,
    fold_id: str,
    seeds: list[int],
    config: dict,
    device: torch.device,
    use_tta: bool = False,
    output_dir: Optional[Path] = None,
) -> dict:
    """Evaluate ensemble of models."""
    print(f"\n{'='*60}")
    print("Ensemble Evaluation")
    print(f"{'='*60}")
    print(f"Fold: {fold_id}")
    print(f"Seeds: {seeds}")
    print(f"TTA: {use_tta}")
    print()

    # Load models
    print("Loading models...")
    models = load_ensemble_models(checkpoint_dir, seeds, fold_id, config, device)
    print(f"Loaded {len(models)} models")

    if len(models) == 0:
        raise ValueError("No models loaded!")

    # Create dataset
    dataset = RehabDataset(
        data_dir=str(data_dir),
        source_dir="",
        split_manifest_csv=str(val_manifest),
        split='val',
        normalization_json=str(norm_json),
        fold_id=fold_id,
        apply_augmentation=False,
    )

    dataloader = DataLoader(
        dataset,
        batch_size=16,
        shuffle=False,
        num_workers=4,
    )

    print(f"Dataset size: {len(dataset)}")

    # Evaluate
    predictions, labels, probabilities = ensemble_predict(
        models, dataloader, device, use_tta=use_tta
    )

    # Compute metrics
    metrics = detailed_evaluation(predictions, labels)

    # Confusion matrix
    conf_matrix = confusion_matrix(labels, predictions)

    print(f"\n{'='*60}")
    print("Results")
    print(f"{'='*60}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Macro F1: {metrics['macro_f1']:.4f}")
    print(f"Macro Precision: {metrics['macro_precision']:.4f}")
    print(f"Macro Recall: {metrics['macro_recall']:.4f}")

    print(f"\nPer-class F1:")
    for class_name, class_metrics in metrics['per_class'].items():
        print(f"  {class_name}: {class_metrics['f1_score']:.4f} (support: {class_metrics['support']})")

    print(f"\nConfusion Matrix:")
    print(conf_matrix)

    # Save results
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'fold_id': fold_id,
            'seeds': seeds,
            'num_models': len(models),
            'use_tta': use_tta,
            'metrics': metrics,
            'confusion_matrix': conf_matrix.tolist(),
            'timestamp': datetime.now().isoformat(),
        }

        output_path = output_dir / f"ensemble_fold_{fold_id}.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_path}")

    return {
        'metrics': metrics,
        'confusion_matrix': conf_matrix,
        'num_models': len(models),
    }


def compare_single_vs_ensemble(
    checkpoint_dir: Path,
    data_dir: Path,
    val_manifest: Path,
    norm_json: Path,
    fold_id: str,
    seeds: list[int],
    config: dict,
    device: torch.device,
    output_dir: Optional[Path] = None,
) -> dict:
    """Compare single model vs ensemble performance."""
    results = {}

    # Single model (first seed only)
    print("\n" + "="*60)
    print("Single Model Evaluation (seed={})".format(seeds[0]))
    print("="*60)

    single_result = evaluate_ensemble(
        checkpoint_dir, data_dir, val_manifest, norm_json,
        fold_id, [seeds[0]], config, device,
        use_tta=False, output_dir=output_dir
    )
    results['single'] = single_result['metrics']

    # Ensemble without TTA
    print("\n" + "="*60)
    print(f"Ensemble Evaluation (seeds={seeds}, no TTA)")
    print("="*60)

    ensemble_result = evaluate_ensemble(
        checkpoint_dir, data_dir, val_manifest, norm_json,
        fold_id, seeds, config, device,
        use_tta=False, output_dir=output_dir
    )
    results['ensemble_no_tta'] = ensemble_result['metrics']

    # Ensemble with TTA
    print("\n" + "="*60)
    print(f"Ensemble Evaluation (seeds={seeds}, with TTA)")
    print("="*60)

    ensemble_tta_result = evaluate_ensemble(
        checkpoint_dir, data_dir, val_manifest, norm_json,
        fold_id, seeds, config, device,
        use_tta=True, output_dir=output_dir
    )
    results['ensemble_with_tta'] = ensemble_tta_result['metrics']

    # Summary
    print("\n" + "="*60)
    print("Comparison Summary")
    print("="*60)
    print(f"{'Method':<25} {'Accuracy':<12} {'Macro F1':<12}")
    print("-"*49)
    print(f"{'Single Model':<25} {results['single']['accuracy']:<12.4f} {results['single']['macro_f1']:<12.4f}")
    print(f"{'Ensemble (no TTA)':<25} {results['ensemble_no_tta']['accuracy']:<12.4f} {results['ensemble_no_tta']['macro_f1']:<12.4f}")
    print(f"{'Ensemble + TTA':<25} {results['ensemble_with_tta']['accuracy']:<12.4f} {results['ensemble_with_tta']['macro_f1']:<12.4f}")

    # Improvement
    single_f1 = results['single']['macro_f1']
    ensemble_f1 = results['ensemble_no_tta']['macro_f1']
    ensemble_tta_f1 = results['ensemble_with_tta']['macro_f1']

    print(f"\nImprovement over single:")
    print(f"  Ensemble: +{(ensemble_f1 - single_f1)*100:.2f}% F1")
    print(f"  Ensemble+TTA: +{(ensemble_tta_f1 - single_f1)*100:.2f}% F1")

    if output_dir:
        summary_path = output_dir / "ensemble_comparison.json"
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSummary saved to: {summary_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Multi-seed ensemble evaluation")

    parser.add_argument("--checkpoint_dir", type=str, required=True,
                        help="Directory containing model checkpoints")
    parser.add_argument("--data_dir", type=str, required=True,
                        help="Path to processed keypoints")
    parser.add_argument("--val_manifest", type=str, required=True,
                        help="Path to validation manifest CSV")
    parser.add_argument("--norm_json", type=str, required=True,
                        help="Path to normalization JSON")
    parser.add_argument("--fold_id", type=str, required=True,
                        help="Fold identifier")
    parser.add_argument("--seeds", type=int, nargs='+', default=DEFAULT_SEEDS,
                        help="Random seeds for ensemble")
    parser.add_argument("--use_tta", action='store_true',
                        help="Use Test-Time Augmentation")
    parser.add_argument("--compare", action='store_true',
                        help="Compare single vs ensemble")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Output directory for results")

    args = parser.parse_args()

    # Setup
    device = select_training_device()

    # Model config (must match training)
    config = {
        'num_exercises': 4,
        'use_hand': True,
        'use_kinematic': True,
        'use_contrastive': False,
        'use_mstcn': True,
        'use_attention': False,
        'upper_limb_only': True,
    }

    output_dir = Path(args.output_dir) if args.output_dir else None

    if args.compare:
        results = compare_single_vs_ensemble(
            checkpoint_dir=Path(args.checkpoint_dir),
            data_dir=Path(args.data_dir),
            val_manifest=Path(args.val_manifest),
            norm_json=Path(args.norm_json),
            fold_id=args.fold_id,
            seeds=args.seeds,
            config=config,
            device=device,
            output_dir=output_dir,
        )
    else:
        results = evaluate_ensemble(
            checkpoint_dir=Path(args.checkpoint_dir),
            data_dir=Path(args.data_dir),
            val_manifest=Path(args.val_manifest),
            norm_json=Path(args.norm_json),
            fold_id=args.fold_id,
            seeds=args.seeds,
            config=config,
            device=device,
            use_tta=args.use_tta,
            output_dir=output_dir,
        )

    print("\nDone!")


if __name__ == "__main__":
    main()
