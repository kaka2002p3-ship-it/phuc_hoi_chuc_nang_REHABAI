"""Build strict evaluator configs for completed RehabMotionNet ablations."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/stage3_upper_limb/processed/keypoints"
SOURCE = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
LOSO = ROOT / "data/stage3_upper_limb/loso"
ABLATION = ROOT / "experiments/ablation"
REPORTS = ROOT / "reports/evaluation"
MAPPING = {"0": "Exercise_1", "1": "Exercise_2", "2": "Exercise_3", "3": "Exercise_4"}
CONFIGS = {
    "full": dict(use_hand=True, use_kinematic=True, use_contrastive=True, use_mstcn=True, use_attention=True),
    "minus_hand": dict(use_hand=False, use_kinematic=True, use_contrastive=True, use_mstcn=True, use_attention=True),
    "minus_kinematic": dict(use_hand=True, use_kinematic=False, use_contrastive=True, use_mstcn=True, use_attention=True),
    "minus_contrastive": dict(use_hand=True, use_kinematic=True, use_contrastive=False, use_mstcn=True, use_attention=True),
    "minus_mstcn": dict(use_hand=True, use_kinematic=True, use_contrastive=True, use_mstcn=False, use_attention=True),
    "minus_attention": dict(use_hand=True, use_kinematic=True, use_contrastive=True, use_mstcn=True, use_attention=False),
}


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    for name, config in CONFIGS.items():
        jobs = []
        for i in range(1, 11):
            fold = f"fold_{i:02d}"
            fd = LOSO / fold
            checkpoint = (
                ROOT / "experiments/upper_limb_v1/training/checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"
                if name == "full"
                else ABLATION / name / "checkpoints" / fold / f"RehabMotionNet_{fold}_supervised_model.pth"
            )
            jobs.append({
                "fold_id": fold, "model_name": "RehabMotionNet",
                "data_dir": str(DATA), "source_dir": str(SOURCE),
                "split_manifest": str(fd / "test_manifest.csv"),
                "normalization_json": str(fd / "normalization.json"),
                "checkpoint_path": str(checkpoint),
                "fold_metadata_path": str(fd / "metadata.json"),
                "expected_model_config": {**config, "upper_limb_only": True},
                "expected_architecture_signature": "rehab_motionnet_upper_limb_v2",
                "expected_class_mapping": MAPPING,
            })
        path = ABLATION / name / "eval_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"jobs": jobs, "output_file": str(REPORTS / f"loso_ablation_{name}.json")}, indent=2), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
