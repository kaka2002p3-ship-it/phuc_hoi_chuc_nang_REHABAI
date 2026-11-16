"""Validate and summarize all five IntelliRehabDS source-subject SSL folds."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.intellirehab_ssl import validate_ssl_artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--encoder-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    folds = []
    losses = []
    validation_subjects = set()
    for fold in range(5):
        artifact = args.encoder_dir / f"fold_{fold}.pth"
        metadata = validate_ssl_artifact(artifact, args.manifest, fold)
        summary_path = artifact.with_suffix(".summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        loss = float(summary["best_validation_loss"])
        if not (loss >= 0.0 and loss < float("inf")):
            raise ValueError(f"Non-finite source validation loss in fold {fold}")
        subjects = set(metadata["validation_subjects"])
        if validation_subjects & subjects:
            raise ValueError("A source subject appears in multiple validation folds")
        validation_subjects.update(subjects)
        losses.append(loss)
        folds.append({
            "source_fold": fold,
            "best_epoch": int(metadata["best_epoch"]),
            "best_validation_loss": loss,
            "training_subject_count": len(metadata["training_subjects"]),
            "validation_subjects": sorted(subjects),
            "transfer_encoder": fold == 0,
        })
    result = {
        "protocol": "five subject-disjoint IntelliRehabDS SSL folds",
        "folds": folds,
        "validation_loss": {
            "mean": statistics.mean(losses),
            "std": statistics.stdev(losses),
            "min": min(losses),
            "max": max(losses),
        },
        "validation_subject_count": len(validation_subjects),
        "predeclared_transfer_source_fold": 0,
        "selected_by_source_score": False,
        "product_label_mapping": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
