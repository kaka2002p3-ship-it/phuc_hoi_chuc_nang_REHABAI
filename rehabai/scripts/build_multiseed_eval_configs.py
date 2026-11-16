"""Build strict evaluator configs for the predeclared multi-seed confirmation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/multiseed_confirmation"
LOSO = ROOT / "data/stage3_upper_limb/loso"
MAPPING = {"0": "Exercise_1", "1": "Exercise_2", "2": "Exercise_3", "3": "Exercise_4"}
CONFIGS = {
    "full_v2": dict(use_hand=True, use_kinematic=True, use_contrastive=True, use_mstcn=True, use_attention=True, upper_limb_only=True),
    "optimized_v1": dict(use_hand=True, use_kinematic=True, use_contrastive=False, use_mstcn=True, use_attention=False, upper_limb_only=True),
}


def main():
    for seed in (7, 2026):
        for candidate, config in CONFIGS.items():
            experiment = BASE / f"{candidate}_seed_{seed}"
            jobs = []
            for i in range(1, 11):
                fold = f"fold_{i:02d}"
                fd = LOSO / fold
                jobs.append({
                    "fold_id": fold, "model_name": "RehabMotionNet",
                    "data_dir": str(ROOT / "data/stage3_upper_limb/processed/keypoints"),
                    "source_dir": str(ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"),
                    "split_manifest": str(fd / "test_manifest.csv"),
                    "normalization_json": str(fd / "normalization.json"),
                    "checkpoint_path": str(experiment / "checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"),
                    "fold_metadata_path": str(fd / "metadata.json"),
                    "expected_model_config": config,
                    "expected_architecture_signature": "rehab_motionnet_upper_limb_v2",
                    "expected_class_mapping": MAPPING,
                })
            experiment.mkdir(parents=True, exist_ok=True)
            path = experiment / "eval_config.json"
            path.write_text(json.dumps({
                "jobs": jobs,
                "output_file": str(ROOT / f"reports/evaluation/loso_{candidate}_seed_{seed}.json"),
            }, indent=2), encoding="utf-8")
            print(path)


if __name__ == "__main__":
    main()
