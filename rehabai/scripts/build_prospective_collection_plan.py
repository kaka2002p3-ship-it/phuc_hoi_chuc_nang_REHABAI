"""Build a balanced, pseudonymous prospective RehabAI collection plan."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", type=int, default=10)
    parser.add_argument("--repeats-per-cell", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.subjects < 10:
        raise ValueError("Prospective gate requires at least 10 new subjects")
    if args.repeats_per_cell < 5:
        raise ValueError("Each subject/exercise/completion cell requires at least 5 repetitions")
    rows = []
    for subject in range(1, args.subjects + 1):
        subject_id = f"P{subject:03d}"
        for exercise in range(1, 5):
            for completion in (0, 1):
                for repetition in range(1, args.repeats_per_cell + 1):
                    filename = f"{subject_id}_E{exercise}_C{completion}_R{repetition:02d}.mp4"
                    rows.append({
                        "subject_id": subject_id,
                        "exercise_id": exercise,
                        "completion_label": completion,
                        "repetition": repetition,
                        "planned_filename": filename,
                        "consent_confirmed": False,
                        "protocol_version": "prospective-v1",
                        "recording_status": "PLANNED",
                        "reviewer": "",
                        "notes": "",
                    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"plan={args.output.resolve()} rows={len(rows)} subjects={args.subjects}")


if __name__ == "__main__":
    main()
