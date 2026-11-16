"""Read-only structural audit for downloaded public auxiliary datasets.

This audit deliberately does not map source tasks to RehabAI's four product
classes and does not add any sample to a training manifest.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "RehabAI_Datasets_FULL_VERIFIED"
    / "04_Public_Auxiliary_2026"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subject_hint(dataset: str, name: str) -> str:
    patterns = {
        "intellirehabds": r"(?:^|[/\\])(\d+)_\d+_\d+_\d+_[12]_[A-Za-z]+\.txt$",
        "armin5_fusion": r"subject_(\d+)\.mat$",
        "stroke_functional_reaching": r"(?:^|[/\\])S(\d+)_",
        "stroke_robot_aided_kinematics": r"(?:^|[/\\])Pat(\d+)_",
    }
    match = re.search(patterns.get(dataset, r"a^"), name, re.IGNORECASE)
    return match.group(1) if match else ""


def main() -> None:
    root = DEFAULT_ROOT
    marker = root / "DOWNLOAD_COMPLETE.json"
    if not marker.is_file():
        raise FileNotFoundError(f"Download is not complete: {marker}")
    manifest_path = root / "download_manifest.csv"
    with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    if not manifest:
        raise ValueError("Download manifest is empty")

    hash_failures = []
    for row in manifest:
        path = Path(row["local_path"])
        if not path.is_file() or sha256(path) != row["sha256"]:
            hash_failures.append(str(path))
    if hash_failures:
        raise ValueError(f"SHA-256 verification failed: {hash_failures}")

    audit_rows = []
    dataset_summaries = {}
    for dataset_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        dataset = dataset_dir.name
        files = [
            path
            for path in dataset_dir.rglob("*")
            if path.is_file() and path.name != "zenodo_record.json"
        ]
        extracted = [path for path in files if "extracted" in path.parts]
        source_files = extracted or [path for path in files if "raw" in path.parts]
        subjects = set()
        extensions = Counter()
        for path in source_files:
            rel = path.relative_to(dataset_dir).as_posix()
            extensions[path.suffix.lower() or "<none>"] += 1
            hint = subject_hint(dataset, rel)
            if hint:
                subjects.add(hint)
            audit_rows.append(
                {
                    "dataset": dataset,
                    "relative_path": rel,
                    "bytes": path.stat().st_size,
                    "extension": path.suffix.lower(),
                    "subject_hint": hint,
                    "sha256": sha256(path),
                    "eligible_for_product_label_mapping": False,
                    "training_status": "NOT_ADMITTED",
                }
            )
        dataset_summaries[dataset] = {
            "file_count": len(source_files),
            "bytes": sum(path.stat().st_size for path in source_files),
            "subject_hint_count": len(subjects),
            "subject_hints": sorted(subjects),
            "extensions": dict(sorted(extensions.items())),
            "product_label_mapping_allowed": False,
            "training_status": "NOT_ADMITTED_PENDING_ADAPTER_REVIEW",
        }

    audit_csv = root / "structural_audit.csv"
    with audit_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    summary = {
        "audit_status": "PASS_STRUCTURAL_ONLY",
        "all_download_sha256_verified": True,
        "product_registry_unchanged": True,
        "source_labels_mapped_to_product_registry": False,
        "training_started": False,
        "datasets": dataset_summaries,
        "limitations": [
            "Structural audit does not establish target-domain compatibility.",
            "These sources cannot serve as independent validation for the four RehabAI exercises.",
            "A source-specific adapter/pretraining protocol must be predeclared before use.",
        ],
    }
    (root / "STRUCTURAL_AUDIT.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
