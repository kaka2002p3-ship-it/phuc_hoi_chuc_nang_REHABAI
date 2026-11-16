"""Read-only preflight checks for Phase 4.7 Stage 3 real-data extraction."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = PROJECT_ROOT / "data" / "indexes" / "upper_limb_master.csv"
DEFAULT_SOURCE_ROOT = (
    PROJECT_ROOT.parent
    / "RehabAI_Datasets_FULL_VERIFIED"
    / "01_Upper_Limb_Stroke"
)
DEFAULT_WORK_ROOT = PROJECT_ROOT / "data" / "stage3_real"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "phase_4_7" / "stage3_preflight.json"
REQUIRED_COLUMNS = {
    "dataset",
    "file",
    "relative_path",
    "subject_id",
    "exercise_id",
    "completion_label",
}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _add(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def run_preflight(
    index_csv: Path,
    source_root: Path,
    work_root: Path,
    expected_videos: int = 491,
    expected_subjects: int = 10,
    check_dependencies: bool = True,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {}

    try:
        source_resolved = source_root.resolve(strict=True)
        _add(checks, "source_root_exists", source_resolved.is_dir(), str(source_resolved))
    except OSError as exc:
        source_resolved = source_root.resolve()
        _add(checks, "source_root_exists", False, str(exc))

    _add(checks, "index_exists", index_csv.is_file(), str(index_csv.resolve()))
    if not index_csv.is_file():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "FAIL",
            "checks": checks,
            "inventory": inventory,
        }

    try:
        frame = pd.read_csv(index_csv, dtype={"subject_id": str})
    except Exception as exc:
        _add(checks, "index_readable", False, repr(exc))
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "FAIL",
            "checks": checks,
            "inventory": inventory,
        }

    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    _add(checks, "required_columns", not missing_columns, f"missing={missing_columns}")
    if missing_columns:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "FAIL",
            "checks": checks,
            "inventory": inventory,
        }

    subjects = frame["subject_id"].astype(str).str.zfill(2)
    exercises = pd.to_numeric(frame["exercise_id"], errors="coerce")
    labels = frame["completion_label"].astype(str).str.strip().str.lower()
    inventory.update(
        {
            "index_rows": int(len(frame)),
            "subjects": dict(sorted(Counter(subjects).items())),
            "exercises": {
                str(int(key)): int(value)
                for key, value in sorted(Counter(exercises.dropna().astype(int)).items())
            },
            "completion_labels": dict(sorted(Counter(labels).items())),
        }
    )

    _add(
        checks,
        "expected_video_count",
        len(frame) == expected_videos,
        f"expected={expected_videos}, actual={len(frame)}",
    )
    _add(
        checks,
        "expected_subject_count",
        subjects.nunique() == expected_subjects,
        f"expected={expected_subjects}, actual={subjects.nunique()}, ids={sorted(subjects.unique())}",
    )
    _add(
        checks,
        "exercise_ids",
        set(exercises.dropna().astype(int)) == {1, 2, 3, 4} and not exercises.isna().any(),
        f"actual={sorted(exercises.dropna().astype(int).unique())}",
    )
    _add(
        checks,
        "completion_labels",
        set(labels) == {"complete", "incomplete"},
        f"actual={sorted(labels.unique())}",
    )

    duplicate_files = frame["file"].astype(str).duplicated().sum()
    duplicate_relative = frame["relative_path"].astype(str).duplicated().sum()
    _add(checks, "unique_source_files", duplicate_files == 0, f"duplicates={duplicate_files}")
    _add(checks, "unique_relative_paths", duplicate_relative == 0, f"duplicates={duplicate_relative}")

    missing_files: list[str] = []
    outside_root: list[str] = []
    relative_mismatches: list[str] = []
    wrong_extensions: list[str] = []
    total_source_bytes = 0
    for row in frame.to_dict("records"):
        raw_path = Path(str(row["file"]))
        if raw_path.suffix.lower() != ".mp4":
            wrong_extensions.append(str(raw_path))
        try:
            resolved = raw_path.resolve(strict=True)
        except OSError:
            missing_files.append(str(raw_path))
            continue
        if not resolved.is_relative_to(source_resolved):
            outside_root.append(str(resolved))
            continue
        total_source_bytes += resolved.stat().st_size
        try:
            relative_candidate = (source_resolved / str(row["relative_path"])).resolve(strict=True)
        except OSError:
            relative_mismatches.append(str(row["relative_path"]))
            continue
        if relative_candidate != resolved:
            relative_mismatches.append(str(row["relative_path"]))

    inventory["source_bytes"] = total_source_bytes
    inventory["source_gib"] = round(total_source_bytes / (1024**3), 3)
    _add(checks, "all_source_files_exist", not missing_files, f"missing={len(missing_files)}; examples={missing_files[:3]}")
    _add(checks, "all_sources_within_root", not outside_root, f"outside={len(outside_root)}; examples={outside_root[:3]}")
    _add(checks, "relative_paths_match", not relative_mismatches, f"mismatches={len(relative_mismatches)}; examples={relative_mismatches[:3]}")
    _add(checks, "mp4_only", not wrong_extensions, f"wrong={len(wrong_extensions)}; examples={wrong_extensions[:3]}")

    legacy_roots = {
        (PROJECT_ROOT / "data" / "interim" / "keypoints").resolve(),
        (PROJECT_ROOT / "data" / "processed" / "keypoints").resolve(),
        (PROJECT_ROOT / "data" / "indexes").resolve(),
    }
    work_resolved = work_root.resolve()
    safe_work_root = work_resolved not in legacy_roots and work_resolved == DEFAULT_WORK_ROOT.resolve()
    _add(
        checks,
        "isolated_stage3_work_root",
        safe_work_root,
        f"required={DEFAULT_WORK_ROOT.resolve()}, actual={work_resolved}",
    )

    disk_anchor = work_resolved
    while not disk_anchor.exists() and disk_anchor.parent != disk_anchor:
        disk_anchor = disk_anchor.parent
    disk = shutil.disk_usage(disk_anchor)
    inventory["free_disk_gib"] = round(disk.free / (1024**3), 3)
    minimum_free = max(2 * total_source_bytes, 5 * 1024**3)
    _add(
        checks,
        "free_disk_space",
        disk.free >= minimum_free,
        f"free_gib={disk.free / (1024**3):.2f}, conservative_required_gib={minimum_free / (1024**3):.2f}",
    )

    if check_dependencies:
        failures = []
        for module_name in ("cv2", "mediapipe", "numpy", "pandas"):
            try:
                module = importlib.import_module(module_name)
                inventory[f"{module_name}_version"] = str(getattr(module, "__version__", "unknown"))
            except Exception as exc:
                failures.append(f"{module_name}: {exc!r}")
        _add(checks, "python_dependencies", not failures, "; ".join(failures) if failures else f"python={sys.version.split()[0]}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "paths": {
            "index_csv": str(index_csv.resolve()),
            "source_root": str(source_resolved),
            "work_root": str(work_resolved),
        },
        "checks": checks,
        "inventory": inventory,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-csv", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--expected-videos", type=int, default=491)
    parser.add_argument("--expected-subjects", type=int, default=10)
    parser.add_argument("--skip-dependency-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_preflight(
        args.index_csv,
        args.source_root,
        args.work_root,
        expected_videos=args.expected_videos,
        expected_subjects=args.expected_subjects,
        check_dependencies=not args.skip_dependency_check,
    )
    _atomic_json(args.report, result)
    print(f"Stage 3 preflight: {result['status']}")
    for item in result["checks"]:
        marker = "PASS" if item["passed"] else "FAIL"
        print(f"[{marker}] {item['name']}: {item['detail']}")
    print(f"Report: {args.report.resolve()}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
