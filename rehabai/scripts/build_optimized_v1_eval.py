"""Build the strict LOSO evaluator config for the exploratory optimized-v1 model."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments/optimized_v1"
MAPPING = {"0": "Exercise_1", "1": "Exercise_2", "2": "Exercise_3", "3": "Exercise_4"}
MODEL_CONFIG = {
    "use_hand": True,
    "use_kinematic": True,
    "use_contrastive": False,
    "use_mstcn": True,
    "use_attention": False,
    "upper_limb_only": True,
}


def main() -> None:
    jobs = []
    for i in range(1, 11):
        fold = f"fold_{i:02d}"
        fd = ROOT / "data/stage3_upper_limb/loso" / fold
        jobs.append({
            "fold_id": fold,
            "model_name": "RehabMotionNet",
            "data_dir": str(ROOT / "data/stage3_upper_limb/processed/keypoints"),
            "source_dir": str(ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"),
            "split_manifest": str(fd / "test_manifest.csv"),
            "normalization_json": str(fd / "normalization.json"),
            "checkpoint_path": str(EXPERIMENT / "checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"),
            "fold_metadata_path": str(fd / "metadata.json"),
            "expected_model_config": MODEL_CONFIG,
            "expected_architecture_signature": "rehab_motionnet_upper_limb_v2",
            "expected_class_mapping": MAPPING,
        })
    EXPERIMENT.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENT / "eval_config.json"
    path.write_text(json.dumps({
        "jobs": jobs,
        "output_file": str(ROOT / "reports/evaluation/loso_optimized_v1.json"),
    }, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
