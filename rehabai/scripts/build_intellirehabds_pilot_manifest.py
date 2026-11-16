"""Build a source-subject manifest for the locked IntelliRehabDS pilot.

This does not create a product manifest and cannot be consumed by the product
LOSO trainer without an explicit adapter implementation.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/data_provenance/intellirehabds_sequence_audit.csv"
OUT = ROOT / "experiments/public_auxiliary_pilot"


def main() -> None:
    rows = list(csv.DictReader(AUDIT.open(encoding="utf-8-sig", newline="")))
    valid = [
        row
        for row in rows
        if row["status"] == "PASS"
        and row["correct"] in {"1", "2"}
        and row["subject_id"] != "217"
    ]
    if len(valid) != 2483:
        raise ValueError(f"Expected 2483 admissible sequences, got {len(valid)}")
    subjects = sorted({row["subject_id"] for row in valid})
    folds = {subject: index % 5 for index, subject in enumerate(subjects)}
    manifest_rows = []
    for row in valid:
        manifest_rows.append(
            {
                "sample_id": Path(row["relative_path"]).stem,
                "source_dataset": "IntelliRehabDS",
                "source_path": str(
                    ROOT.parent
                    / "RehabAI_Datasets_FULL_VERIFIED/04_Public_Auxiliary_2026/intellirehabds/extracted/SkeletonData/SkeletonData"
                    / row["relative_path"]
                ),
                "subject_id": row["subject_id"],
                "session_id": row["session_id"],
                "source_gesture": row["gesture"],
                "repetition": row["repetition"],
                "source_correctness": row["correct"],
                "position": row["position"],
                "frame_count": row["frame_count"],
                "source_fold": folds[row["subject_id"]],
                "product_label": "NOT_APPLICABLE",
                "product_split": "NOT_ADMITTED",
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "intellirehabds_pilot_manifest.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    summary = {
        "manifest": str(path),
        "sequence_count": len(manifest_rows),
        "subject_count": len(subjects),
        "source_subject_folds": 5,
        "source_subjects": subjects,
        "binary_source_correctness_only": True,
        "excluded_source_subjects": ["217"],
        "exclusion_reason": "source record states subject 217 stopped exercises mid-recording",
        "product_label_mapping": False,
        "product_training_admitted": False,
    }
    (OUT / "intellirehabds_pilot_manifest.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
