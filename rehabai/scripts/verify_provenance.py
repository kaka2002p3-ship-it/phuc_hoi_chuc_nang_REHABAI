import argparse
import os
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd

from shared.provenance import verify_and_grant_real_verified


def verify_manifest(
    input_csv: str,
    output_csv: str,
    source_root: str,
    processed_root: str,
    verification_key: Optional[str] = None,
) -> Path:
    """Verify every candidate physically and publish a signed manifest atomically."""
    input_path = Path(input_csv).resolve(strict=True)
    source_path = Path(source_root).resolve(strict=True)
    processed_path = Path(processed_root).resolve(strict=True)
    records = pd.read_csv(input_path, dtype={"subject_id": str}).to_dict("records")
    if not records:
        raise ValueError("Candidate provenance manifest is empty")

    verified = [
        verify_and_grant_real_verified(
            record,
            str(source_path),
            str(processed_path),
            verification_key=verification_key,
        )
        for record in records
    ]

    target = Path(output_csv).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
        )
        os.close(descriptor)
        temp_path = Path(temp_name)
        pd.DataFrame(verified).to_csv(temp_path, index=False)
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--processed-root", required=True)
    args = parser.parse_args()
    result = verify_manifest(
        args.input_csv,
        args.output_csv,
        args.source_root,
        args.processed_root,
    )
    print(f"Verified manifest written to {result}")


if __name__ == "__main__":
    main()
