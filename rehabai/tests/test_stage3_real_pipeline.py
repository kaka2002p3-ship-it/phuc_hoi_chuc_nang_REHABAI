from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.extract_keypoints import compute_sha256, prepare_tasks
from scripts.process_features import process_one
from scripts.stage3_preflight import DEFAULT_WORK_ROOT, run_preflight
from shared.provenance import STATUS_REAL_CANDIDATE


def write_index(path: Path, source: Path, relative: str = "dataset/sample.mp4") -> None:
    pd.DataFrame([{
        "dataset": "Upper_Limb_Stroke",
        "file": str(source),
        "relative_path": relative,
        "subject_id": "01",
        "exercise_id": 1,
        "completion_label": "complete",
    }]).to_csv(path, index=False)


def test_preflight_accepts_contained_unique_inventory(tmp_path):
    source_root = tmp_path / "source"
    video = source_root / "dataset" / "sample.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"test-video")
    index = tmp_path / "index.csv"
    write_index(index, video)

    result = run_preflight(
        index,
        source_root,
        DEFAULT_WORK_ROOT,
        expected_videos=1,
        expected_subjects=1,
        check_dependencies=False,
    )

    assert result["status"] == "FAIL"
    failures = {item["name"] for item in result["checks"] if not item["passed"]}
    assert failures == {"exercise_ids", "completion_labels"}


def test_prepare_tasks_rejects_source_outside_root(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"video")
    index = tmp_path / "index.csv"
    write_index(index, outside, "outside.mp4")

    with pytest.raises(ValueError, match="escapes source root"):
        prepare_tasks(index, source_root, tmp_path / "output", {}, False)


def test_prepare_tasks_resumes_only_matching_hashes(tmp_path):
    source_root = tmp_path / "source"
    video = source_root / "dataset" / "sample.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    index = tmp_path / "index.csv"
    write_index(index, video)
    output_dir = tmp_path / "output"

    tasks, resumed = prepare_tasks(index, source_root, output_dir, {}, False)
    assert len(tasks) == 1 and not resumed
    task = tasks[0]
    output_dir.mkdir()
    output = output_dir / task["output"]
    output.write_bytes(b"feature")
    prior = {
        **{key: task[key] for key in (
            "dataset", "file", "source_relative_path", "source_sha256",
            "subject_id", "exercise_id", "completion_label", "output",
        )},
        "output_sha256": compute_sha256(output),
        "status": "success",
        "extractor_version": "MediaPipe Holistic real-v1",
    }

    tasks, resumed = prepare_tasks(
        index, source_root, output_dir, {task["source_relative_path"]: prior}, False
    )
    assert not tasks and len(resumed) == 1


def test_process_one_creates_valid_real_candidate(tmp_path):
    source_root = tmp_path / "source"
    source = source_root / "dataset" / "sample.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"real-video")
    interim_dir = tmp_path / "interim"
    processed_dir = tmp_path / "processed"
    interim_dir.mkdir()
    processed_dir.mkdir()
    interim = interim_dir / "sample.npz"
    frames = 40
    pose = np.ones((frames, 33, 4), dtype=np.float32)
    left = np.ones((frames, 21, 3), dtype=np.float32)
    right = np.ones((frames, 21, 3), dtype=np.float32)
    np.savez_compressed(
        interim,
        pose_landmarks=pose,
        pose_world_landmarks=pose,
        left_hand_landmarks=left,
        right_hand_landmarks=right,
        timestamps=np.arange(frames, dtype=np.float32) * (1000.0 / 30.0),
        frame_indices=np.arange(frames, dtype=np.int32),
        fps=np.asarray(30.0, dtype=np.float32),
    )
    row = {
        "dataset": "Upper_Limb_Stroke",
        "file": str(source),
        "source_relative_path": "dataset/sample.mp4",
        "source_sha256": compute_sha256(source),
        "subject_id": "01",
        "exercise_id": 1,
        "completion_label": "complete",
        "output": interim.name,
        "output_sha256": compute_sha256(interim),
        "status": "success",
        "extractor_version": "MediaPipe Holistic real-v1",
    }

    candidate = process_one(row, source_root, interim_dir, processed_dir, False)

    assert candidate["data_status"] == STATUS_REAL_CANDIDATE
    assert candidate["source_record_id"] == "dataset/sample.mp4"
    assert candidate["completion_label"] == 1.0
    assert (processed_dir / "sample.npz").is_file()

    resumed = process_one(row, source_root, interim_dir, processed_dir, False)
    assert resumed["processed_feature_sha256"] == candidate["processed_feature_sha256"]


def test_process_one_rejects_mock_extractor_before_output(tmp_path):
    row = {"extractor_version": "MediaPipe Mock"}
    with pytest.raises(ValueError, match="forbidden"):
        process_one(row, tmp_path, tmp_path, tmp_path, False)
