"""Evaluate the task-specific research hybrid.

Exercise logits come from optimized-v1; completion logits come from the
combined datanew SSL candidate. Both models are loaded under the strict fold
provenance contract and evaluated on the same unchanged test manifest.
This script only writes a research report; it never changes production.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from shared.metrics import accuracy_score, precision_recall_fscore_support
from training.checkpoint_utils import compute_file_sha256, load_checkpoint_strict
from training.datasets.rehab_dataset import RehabDataset
from training.model_registry import get_model

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
DATA = ROOT / "data/stage3_upper_limb/processed/keypoints"
REPORTS = ROOT / "reports/evaluation"
EXERCISE_CONFIG = {
    "use_hand": True, "use_kinematic": True, "use_contrastive": False,
    "use_mstcn": True, "use_attention": False, "upper_limb_only": True,
}
COMPLETION_CONFIG = {
    "use_hand": True, "use_kinematic": True, "use_contrastive": True,
    "use_mstcn": True, "use_attention": True, "upper_limb_only": True,
}
CLASS_MAPPING = {0: "Exercise_1", 1: "Exercise_2", 2: "Exercise_3", 3: "Exercise_4"}


def metric(target, prediction, labels):
    p, r, f, support = precision_recall_fscore_support(
        target, prediction, average=None, zero_division=0, labels=labels
    )
    macro = precision_recall_fscore_support(
        target, prediction, average="macro", zero_division=0, labels=labels
    )
    return {
        "accuracy": float(accuracy_score(target, prediction)),
        "precision_macro": float(macro[0]),
        "recall_macro": float(macro[1]),
        "f1_macro": float(macro[2]),
        "per_class": {
            str(label): {"precision": float(p[i]), "recall": float(r[i]),
                         "f1": float(f[i]), "support": int(support[i])}
            for i, label in enumerate(labels)
        },
    }


def load_fold_model(path, fold, fold_dir, config, external=False):
    model = get_model("RehabMotionNet", config=config)
    metadata = json.loads((fold_dir / "metadata.json").read_text(encoding="utf-8"))
    loaded = load_checkpoint_strict(
        filepath=str(path), model=model, expected_model_id="RehabMotionNet",
        expected_fold_id=fold, expected_protocol="1.1",
        expected_provenance_hash=metadata["canonical_provenance_manifest_hash"],
        expected_train_manifest_hash=metadata["canonical_train_manifest_hash"],
        expected_normalization_hash=compute_file_sha256(str(fold_dir / "normalization.json")),
        expected_class_mapping=CLASS_MAPPING,
        expected_model_config=config,
        expected_architecture_signature="rehab_motionnet_upper_limb_v2",
        expected_role="supervised_model", device="cpu",
    )
    if external:
        inputs = loaded["metadata"].get("training_inputs", {})
        encoder = inputs.get("external_encoder", {})
        if encoder.get("architecture_signature") != "datanew_ssl_encoder_v1":
            raise ValueError(f"{fold}: completion checkpoint is not datanew SSL")
        if encoder.get("ontology_mapping_to_product") is not None:
            raise ValueError(f"{fold}: external encoder contains an ontology mapping")
    return model


@torch.no_grad()
def infer(model, loader, device):
    model.eval().to(device)
    ex, comp, target, comp_target = [], [], [], []
    for batch in loader:
        out_ex, out_comp = model(batch["features"].to(device))
        ex.append(out_ex.float().cpu())
        comp.append(out_comp.float().reshape(-1).cpu())
        target.append(batch["exercise"].cpu())
        comp_target.append(batch["completion"].reshape(-1).long().cpu())
    return torch.cat(ex), torch.cat(comp), torch.cat(target), torch.cat(comp_target)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = []
    for i in range(1, 11):
        fold = f"fold_{i:02d}"
        fold_dir = ROOT / "data/stage3_upper_limb/loso" / fold
        dataset = RehabDataset(
            str(DATA), str(SOURCE), str(fold_dir / "test_manifest.csv"), "test",
            str(fold_dir / "normalization.json"), fold, False,
        )
        loader = DataLoader(dataset, batch_size=32, shuffle=False)
        exercise_path = ROOT / "experiments/optimized_v1/checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"
        completion_path = ROOT / "experiments/datanew_ssl_all_full/checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"
        exercise_model = load_fold_model(exercise_path, fold, fold_dir, EXERCISE_CONFIG)
        completion_model = load_fold_model(completion_path, fold, fold_dir, COMPLETION_CONFIG, external=True)
        ex_logits, _, target, comp_target = infer(exercise_model, loader, device)
        _, comp_logits, target2, comp_target2 = infer(completion_model, loader, device)
        if not torch.equal(target, target2) or not torch.equal(comp_target, comp_target2):
            raise ValueError(f"{fold}: task heads saw different target order")
        ex_pred = ex_logits.argmax(1).numpy()
        comp_pred = (torch.sigmoid(comp_logits) >= 0.5).long().numpy()
        target_np, comp_target_np = target.numpy(), comp_target.numpy()
        em = metric(target_np, ex_pred, list(CLASS_MAPPING))
        cm = metric(comp_target_np, comp_pred, [0, 1])
        rows.append({
            "fold_id": fold, "model_name": "HybridOptimizedExerciseDatanewCompletion",
            **em, "completion_accuracy": cm["accuracy"],
            "completion_precision_macro": cm["precision_macro"],
            "completion_recall_macro": cm["recall_macro"],
            "completion_f1_macro": cm["f1_macro"],
            "sample_count": len(dataset), "completion_sample_count": len(dataset),
            "observed_classes": sorted({int(x) for x in target_np}),
            "class_coverage_complete": set(target_np) == set(CLASS_MAPPING),
            "hybrid": {
                "exercise_source": "optimized_v1_seed_42",
                "completion_source": "datanew_ssl_all_full_seed_42",
                "selection": "predeclared_task_specific_heads; no test-fold selection",
            },
        })
        print(f"{fold}: exercise_f1={em['f1_macro']:.4f} completion_f1={cm['f1_macro']:.4f}", flush=True)
        del exercise_model, completion_model
    output = REPORTS / "loso_hybrid_optimized_exercise_datanew_completion.json"
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "exercise_macro_f1": statistics.mean(r["f1_macro"] for r in rows),
        "exercise_accuracy": statistics.mean(r["accuracy"] for r in rows),
        "completion_macro_f1": statistics.mean(r["completion_f1_macro"] for r in rows),
        "completion_accuracy": statistics.mean(r["completion_accuracy"] for r in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
