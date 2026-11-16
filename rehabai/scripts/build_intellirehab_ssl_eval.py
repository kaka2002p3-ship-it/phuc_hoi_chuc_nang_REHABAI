"""Build strict data-01 LOSO evaluation jobs for OptimizedSSLAdapter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = {"0": "Exercise_1", "1": "Exercise_2", "2": "Exercise_3", "3": "Exercise_4"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default="public_auxiliary_pilot/intellirehab_ssl_adapter_v1")
    parser.add_argument("--report-name", default="loso_intellirehab_ssl_adapter_v1.json")
    parser.add_argument("--adapter-dim", type=int, default=64)
    parser.add_argument("--adapter-dropout", type=float, default=0.20)
    args = parser.parse_args()
    experiment = ROOT / "experiments" / args.experiment
    model_config = {
        "num_exercises": 4,
        "adapter_dim": args.adapter_dim,
        "adapter_dropout": args.adapter_dropout,
    }
    jobs = []
    for i in range(1, 11):
        fold = f"fold_{i:02d}"
        fd = ROOT / "data/stage3_upper_limb/loso" / fold
        jobs.append({
            "fold_id": fold,
            "model_name": "OptimizedSSLAdapter",
            "data_dir": str(ROOT / "data/stage3_upper_limb/processed/keypoints"),
            "source_dir": str(ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED/01_Upper_Limb_Stroke"),
            "split_manifest": str(fd / "test_manifest.csv"),
            "normalization_json": str(fd / "normalization.json"),
            "checkpoint_path": str(experiment / "checkpoints" / fold / f"OptimizedSSLAdapter_{fold}_supervised_model.pth"),
            "fold_metadata_path": str(fd / "metadata.json"),
            "expected_model_config": model_config,
            "expected_architecture_signature": "optimized_v1_intellirehab_ssl_adapter_v1",
            "expected_class_mapping": MAPPING,
        })
    experiment.mkdir(parents=True, exist_ok=True)
    output = ROOT / "reports/evaluation" / args.report_name
    path = experiment / "eval_config.json"
    path.write_text(json.dumps({"jobs": jobs, "output_file": str(output)}, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
