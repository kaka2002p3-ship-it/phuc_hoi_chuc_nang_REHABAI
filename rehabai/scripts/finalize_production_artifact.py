"""Add production metadata to an already strictly exported model bundle.

This script never changes model weights.  It derives the model card and
metrics from the checked-in LOSO evaluation JSON and records hashes for every
runtime contract file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", required=True)
    p.add_argument("--evaluation", required=True)
    args = p.parse_args()
    artifact = Path(args.artifact).resolve()
    evaluation = Path(args.evaluation).resolve()
    report = json.loads(evaluation.read_text(encoding="utf-8"))
    folds = [x for x in report if isinstance(x, dict) and x.get("fold_id")]
    if len(folds) != 10:
        raise ValueError(f"Expected 10 LOSO folds, found {len(folds)}")

    def mean(key: str) -> float:
        vals = [float(x[key]) for x in folds if x.get(key) is not None]
        return sum(vals) / len(vals)

    def std(key: str) -> float:
        vals = [float(x[key]) for x in folds if x.get(key) is not None]
        m = sum(vals) / len(vals)
        return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5

    metrics = {
        "evaluation_protocol": "strict subject-wise LOSO, 10 folds",
        "sample_count": 387,
        "exercise": {
            "accuracy_mean": mean("accuracy"),
            "accuracy_std": std("accuracy"),
            "macro_f1_mean": mean("f1_macro"),
            "macro_f1_std": std("f1_macro"),
        },
        "completion": {
            "accuracy_mean": mean("completion_accuracy"),
            "macro_f1_mean": mean("completion_f1_macro"),
            "promoted_to_production": False,
            "reason": "not superior to the v1/balanced binary baseline",
        },
        "limitations": [
            "10 subjects; folds 07-10 have restricted exercise coverage",
            "No clinical error-type labels; error feedback disabled",
        ],
    }
    (artifact / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    registry_hash = sha256(artifact / "exercise_registry.json")
    (artifact / "registry_sha256.txt").write_text(registry_hash + "\n", encoding="utf-8")

    config = json.loads((artifact / "model_config.json").read_text(encoding="utf-8"))
    card = f"""# RehabMotionNet upper-limb v2 model card

## Dataset and task
- Dataset: Upper Limb Stroke, 491 source videos; 387 samples passed the
  upper-limb quality gate.
- Task: four-class exercise recognition. Completion status is reported only
  as an experimental auxiliary head and is not promoted to production.
- Split: strict subject-wise 10-fold LOSO; normalization fitted on each
  training partition only.

## Results
- Exercise Macro-F1: {metrics['exercise']['macro_f1_mean']:.4f} +/- {metrics['exercise']['macro_f1_std']:.4f}
- Exercise accuracy: {metrics['exercise']['accuracy_mean']:.4f} +/- {metrics['exercise']['accuracy_std']:.4f}
- Completion Macro-F1: {metrics['completion']['macro_f1_mean']:.4f} (experimental)

## Runtime contract
- Architecture signature: `{config['architecture_signature']}`
- Input: 96 frames x 237 float32 features
- Upper-limb pose nodes: shoulder, elbow and wrist joints (6 pose nodes)
- Registry SHA-256: `{registry_hash}`

## Limitations and intended use
This is a research/demo inference model. It must not be used as a medical
diagnosis, and it does not replace a qualified healthcare professional.
Error-type feedback and clinical correctness claims are disabled because no
verified expert-labelled extension dataset is available.
"""
    (artifact / "model_card.md").write_text(card, encoding="utf-8")

    manifest = {p.name: sha256(p) for p in sorted(artifact.iterdir()) if p.is_file() and p.name != "bundle_sha256.json"}
    (artifact / "bundle_sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"artifact": str(artifact), "registry_sha256": registry_hash, "files": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()
