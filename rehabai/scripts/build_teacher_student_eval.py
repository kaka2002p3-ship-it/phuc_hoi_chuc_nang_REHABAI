"""Build strict evaluation config for completed teacher-student folds."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
jobs = []
for i in range(1, 11):
    fold = f"fold_{i:02d}"
    jobs.append({
        "fold_id": fold,
        "model_name": "RehabMotionNet",
        "data_dir": str(root / "data/stage3_upper_limb/processed/keypoints"),
        "source_dir": str(root.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"),
        "split_manifest": str(root / f"data/stage3_upper_limb/loso/{fold}/test_manifest.csv"),
        "normalization_json": str(root / f"data/stage3_upper_limb/loso/{fold}/normalization.json"),
        "checkpoint_path": str(root / f"experiments/teacher_student_v1/checkpoints/{fold}/RehabMotionNet_{fold}_supervised_model.pth"),
        "fold_metadata_path": str(root / f"data/stage3_upper_limb/loso/{fold}/metadata.json"),
        "expected_model_config": {
            "use_hand": True, "use_kinematic": True, "use_contrastive": True,
            "use_mstcn": True, "use_attention": True, "upper_limb_only": True,
        },
        "expected_architecture_signature": "rehab_motionnet_upper_limb_v2",
        "expected_class_mapping": {str(j): f"Exercise_{j+1}" for j in range(4)},
    })
out = root / "experiments/teacher_student_v1/eval_config.json"
out.write_text(json.dumps({"jobs": jobs, "output_file": str(root / "reports/evaluation/loso_teacher_student_v1.json")}, indent=2), encoding="utf-8")
print(out)
