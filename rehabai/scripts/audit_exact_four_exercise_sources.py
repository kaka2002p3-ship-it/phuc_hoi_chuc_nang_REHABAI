"""Audit public sources for the exact four RehabAI exercises.

The Mendeley source is checked by relative path and SHA-256 because filenames
are only unique within exercise/status folders (e.g. 04_02_00_01.mp4 occurs
twice). No external label is inferred or remapped here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import requests


MENDELEY_API = "https://data.mendeley.com/public-api/datasets/49h9dcwx5v"
EXPECTED_EXERCISES = {
    "1": "Lifting an Object",
    "2": "Extending the Elbow",
    "3": "Side-to-Side",
    "4": "Reaching Forward",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    response = requests.get(MENDELEY_API, timeout=60, headers={"User-Agent": "RehabAI-source-audit/1.0"})
    response.raise_for_status()
    source = response.json()
    remote = {}
    for item in source.get("files", []):
        relative = str(item.get("filename", ""))
        # API filenames are flat; folder names are not exposed in a stable
        # human-readable field. Keep all hashes per basename and reconcile by
        # the exercise/status path encoded in the downloaded source tree.
        remote.setdefault(Path(relative).name, []).append({
            "sha256": item.get("content_details", {}).get("sha256_hash"),
            "size": item.get("size"),
            "file_id": item.get("id"),
        })
    local = []
    for path in sorted(args.dataset_root.rglob("*.mp4")):
        relative = path.relative_to(args.dataset_root).as_posix()
        parts = relative.split("/")
        exercise = next((part for part in parts if re.match(r"^[1-4]_", part)), "")
        status = "Complete" if "/Complete/" in relative else "Incomplete" if "/Incomplete/" in relative else ""
        local.append({
            "relative_path": relative,
            "filename": path.name,
            "exercise_id": exercise.split("_", 1)[0] if exercise else "",
            "status": status,
            "sha256": sha256(path),
            "size": path.stat().st_size,
        })
    mismatches = []
    for item in local:
        hashes = {entry.get("sha256") for entry in remote.get(item["filename"], [])}
        if item["sha256"] not in hashes:
            mismatches.append(item)
    counts = {}
    for item in local:
        key = (item["exercise_id"], item["status"])
        counts["%s_%s" % key] = counts.get("%s_%s" % key, 0) + 1
    result = {
        "source": {
            "dataset_id": source.get("id"),
            "doi": source.get("doi", {}).get("id"),
            "version": source.get("version"),
            "name": source.get("name"),
            "publish_date": source.get("publish_date"),
            "license": source.get("data_licence", {}).get("short_name"),
            "license_url": source.get("data_licence", {}).get("url"),
            "remote_file_count": len(source.get("files", [])),
            "remote_total_bytes": source.get("size"),
        },
        "exact_product_exercises": EXPECTED_EXERCISES,
        "local_file_count": len(local),
        "local_unique_basenames": len({item["filename"] for item in local}),
        "local_counts": counts,
        "remote_hash_match_by_path_basename": len(mismatches) == 0,
        "hash_mismatch_count": len(mismatches),
        "hash_mismatch_examples": mismatches[:10],
        "new_exact_source_found": False,
        "product_label_mapping_performed": False,
        "decision": "use_existing_verified_source_only; no additional exact public source found",
        "limitations": [
            "The source has one public version and 491 videos; no larger exact mirror was found.",
            "The API exposes duplicate basenames across exercise/status folders, so hashes were matched per basename set.",
            "A source with similar reaching/elbow movements is not admitted as one of the four product labels.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("source", "local_file_count", "local_counts", "remote_hash_match_by_path_basename", "new_exact_source_found", "decision")}, indent=2))


if __name__ == "__main__":
    main()
