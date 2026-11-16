"""Strict Stage 3 -> LOSO research pipeline.

This orchestrator deliberately does not train or evaluate until every input
record has passed physical provenance checks and each fold has a train-only
normalization schema.  It is resumable: completed extraction/processing files
are reused by the underlying atomic scripts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# When invoked as ``python scripts/run_research_pipeline.py`` Python places the
# scripts directory (rather than the project root) first on sys.path.  Bootstrap
# the root so package imports work both as a script and as ``python -m``.
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from scripts.generate_loso import generate_loso_splits, save_folds
from shared.provenance import VERIFICATION_KEY_ENV
from training.normalization import fit_fold_normalization


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT.parent / "RehabAI_Datasets_FULL_VERIFIED" / "01_Upper_Limb_Stroke"
STAGE_ROOT = PROJECT_ROOT / "data" / "stage3_real"
QUALITY_LOG = STAGE_ROOT / "indexes" / "extraction_quality.csv"
CANDIDATES = STAGE_ROOT / "indexes" / "provenance_candidates.csv"
VERIFIED = STAGE_ROOT / "indexes" / "provenance_verified.csv"
INTERIM = STAGE_ROOT / "interim" / "keypoints"
PROCESSED = STAGE_ROOT / "processed" / "keypoints"
LOSO = STAGE_ROOT / "loso"
SECRETS = PROJECT_ROOT / ".secrets" / "provenance_hmac_key.txt"
INDEX = PROJECT_ROOT / "data" / "indexes" / "upper_limb_master.csv"


def _load_key() -> str:
    if not SECRETS.is_file():
        raise FileNotFoundError(f"Missing provenance key: {SECRETS}; run 01_VERIFY_ENV.cmd first")
    key = SECRETS.read_text(encoding="utf-8").strip()
    if len(key) < 32:
        raise ValueError("The local provenance key must contain at least 32 characters")
    os.environ[VERIFICATION_KEY_ENV] = key
    return key


def _run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    # Child scripts import the project packages (``shared``, ``training``).
    # Preserve any caller-provided PYTHONPATH while ensuring the project root
    # is available when the orchestrator is launched from another directory.
    child_env = os.environ.copy()
    existing_path = child_env.get("PYTHONPATH", "")
    child_env["PYTHONPATH"] = (
        str(PROJECT_ROOT)
        if not existing_path
        else str(PROJECT_ROOT) + os.pathsep + existing_path
    )
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=child_env, check=False)
    if completed.returncode:
        raise RuntimeError(f"Pipeline command failed with exit code {completed.returncode}: {command}")


def process_features() -> None:
    _run([
        sys.executable, "scripts/process_features.py",
        "--quality-log", str(QUALITY_LOG),
        "--source-root", str(SOURCE_ROOT),
        "--interim-dir", str(INTERIM),
        "--processed-dir", str(PROCESSED),
        "--provenance-candidates", str(CANDIDATES),
        "--errors", str(STAGE_ROOT / "indexes" / "processing_errors.csv"),
    ])


def extract_real_data(workers: int = 2) -> None:
    """Run resumable MediaPipe extraction into the isolated Stage 3 root."""
    if not 1 <= workers <= 8:
        raise ValueError("workers must be between 1 and 8")
    _run([
        sys.executable, "scripts/extract_keypoints.py",
        "--index-csv", str(INDEX),
        "--source-root", str(SOURCE_ROOT),
        "--output-dir", str(INTERIM),
        "--quality-log", str(QUALITY_LOG),
        "--workers", str(workers),
    ])


def verify_provenance() -> None:
    key = _load_key()
    from scripts.verify_provenance import verify_manifest

    if not CANDIDATES.is_file():
        raise FileNotFoundError(f"Missing provenance candidates: {CANDIDATES}")
    result = verify_manifest(
        str(CANDIDATES), str(VERIFIED), str(SOURCE_ROOT), str(PROCESSED), verification_key=key
    )
    print(f"Signed REAL_VERIFIED manifest: {result}", flush=True)


def generate_loso() -> None:
    _load_key()
    if not VERIFIED.is_file():
        raise FileNotFoundError(f"Missing verified manifest: {VERIFIED}")
    records = pd.read_csv(VERIFIED, dtype={"subject_id": str}).to_dict("records")
    expected_subjects = [f"{index:02d}" for index in range(1, 11)]
    folds = generate_loso_splits(records, expected_subjects, deterministic_seed=42)
    save_folds(folds, str(LOSO))
    print(f"Generated {len(folds)} LOSO folds: {LOSO}", flush=True)


def fit_normalizations() -> None:
    _load_key()
    if not LOSO.is_dir():
        raise FileNotFoundError(f"Missing LOSO directory: {LOSO}")
    for fold_dir in sorted(LOSO.glob("fold_*")):
        metadata_path = fold_dir / "metadata.json"
        train_path = fold_dir / "train_manifest.csv"
        output_path = fold_dir / "normalization.json"
        if not metadata_path.is_file() or not train_path.is_file():
            raise FileNotFoundError(f"Incomplete fold directory: {fold_dir}")
        import json
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        records = pd.read_csv(train_path, dtype={"subject_id": str}).to_dict("records")
        fit_fold_normalization(records, metadata, str(PROCESSED), str(SOURCE_ROOT), str(output_path))
        print(f"{fold_dir.name}: train-only normalization ready", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("extract", "process", "verify", "loso", "normalize", "all"), default="all")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.stage in {"verify", "loso", "normalize", "all"}:
        _load_key()
    if args.stage in {"extract", "all"}:
        extract_real_data(args.workers)
    if args.stage in {"process", "all"}:
        process_features()
    if args.stage in {"verify", "all"}:
        verify_provenance()
    if args.stage in {"loso", "all"}:
        generate_loso()
    if args.stage in {"normalize", "all"}:
        fit_normalizations()
    print("Research data pipeline completed through stage:", args.stage, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
