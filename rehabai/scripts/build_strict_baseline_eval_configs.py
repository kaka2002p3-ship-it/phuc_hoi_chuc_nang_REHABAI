"""Build strict evaluator configs for the completed MLP/LSTM LOSO checkpoints."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/stage3_upper_limb/processed/keypoints"
SOURCE_DIR = ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"
LOSO_DIR = ROOT / "data/stage3_upper_limb/loso"
CHECKPOINT_DIR = ROOT / "experiments/strict_baselines/checkpoints"
EXPERIMENT_DIR = ROOT / "experiments/strict_baselines"
REPORT_DIR = ROOT / "reports/evaluation"
CLASS_MAPPING = {
    "0": "Exercise_1",
    "1": "Exercise_2",
    "2": "Exercise_3",
    "3": "Exercise_4",
}


def _model_config(model_name: str) -> dict:
    config = {"input_dim": 237, "num_exercises": 4}
    if model_name == "lstm":
        config.update({"hidden_size": 64, "num_layers": 1, "bidirectional": False})
    return config


def _build(model_name: str) -> Path:
    jobs = []
    for fold_number in range(1, 11):
        fold_id = f"fold_{fold_number:02d}"
        fold_dir = LOSO_DIR / fold_id
        checkpoint = CHECKPOINT_DIR / fold_id / f"{model_name}_{fold_id}_supervised_model.pth"
        required = [
            DATA_DIR,
            SOURCE_DIR,
            fold_dir / "test_manifest.csv",
            fold_dir / "normalization.json",
            fold_dir / "metadata.json",
            checkpoint,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing strict {model_name} evaluation inputs: {missing}")
        jobs.append({
            "fold_id": fold_id,
            "model_name": model_name,
            "data_dir": str(DATA_DIR),
            "source_dir": str(SOURCE_DIR),
            "split_manifest": str(fold_dir / "test_manifest.csv"),
            "normalization_json": str(fold_dir / "normalization.json"),
            "checkpoint_path": str(checkpoint),
            "fold_metadata_path": str(fold_dir / "metadata.json"),
            "expected_model_config": _model_config(model_name),
            "expected_architecture_signature": f"baseline_{model_name}_v1",
            "expected_class_mapping": CLASS_MAPPING,
            "expected_role": "supervised_model",
            "expected_protocol": "1.1",
        })

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    config_path = EXPERIMENT_DIR / f"loso_{model_name}_eval_config.json"
    payload = {
        "jobs": jobs,
        "output_file": str(REPORT_DIR / f"loso_strict_{model_name}.json"),
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def main() -> None:
    for model_name in ("mlp", "lstm"):
        print(_build(model_name))


if __name__ == "__main__":
    main()
