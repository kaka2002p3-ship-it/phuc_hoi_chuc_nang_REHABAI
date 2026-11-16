import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.generate_loso import generate_loso_splits
from shared.provenance import (
    VERIFICATION_KEY_ENV,
    build_provenance_record,
    verify_and_grant_real_verified,
)

KEY = "loso-test-authority-key-at-least-32-bytes"


class TestLOSO(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        os.environ[VERIFICATION_KEY_ENV] = KEY
        self.eligible_records = []
        for subject_idx in range(1, 11):
            for video_idx in range(1, 3):
                stem = f"sub{subject_idx}_vid{video_idx}"
                source = self.root / f"{stem}.mp4"
                processed = self.root / f"{stem}.npz"
                source.write_bytes(stem.encode("utf-8"))
                np.savez(
                    processed,
                    pose_landmarks=np.zeros((2, 33, 4), dtype=np.float32),
                    left_hand_landmarks=np.zeros((2, 21, 3), dtype=np.float32),
                    right_hand_landmarks=np.zeros((2, 21, 3), dtype=np.float32),
                    kinematics=np.zeros((2, 12), dtype=np.float32),
                )
                candidate = build_provenance_record(
                    str(source),
                    f"{subject_idx:02d}",
                    1,
                    1.0,
                    "success",
                    "mediapipe-1.0",
                    processed_path=str(processed),
                    quality_gate_passed=True,
                    compute_hash=True,
                )
                self.eligible_records.append(
                    verify_and_grant_real_verified(candidate, str(self.root), str(self.root), KEY)
                )
        self.expected_subjects = [f"{index:02d}" for index in range(1, 11)]

    def tearDown(self):
        os.environ.pop(VERIFICATION_KEY_ENV, None)
        self.temp_dir.cleanup()

    def test_loso_generation(self):
        folds = generate_loso_splits(self.eligible_records, self.expected_subjects)
        self.assertEqual(len(folds), 10)
        subjects_seen_as_test = set()
        for fold_data in folds.values():
            metadata = fold_data["metadata"]
            test_subject = metadata["test_subject"]
            val_subject = metadata["validation_subjects"][0]
            train_subjects = metadata["train_subjects"]
            self.assertNotIn(test_subject, subjects_seen_as_test)
            subjects_seen_as_test.add(test_subject)
            self.assertNotIn(test_subject, train_subjects)
            self.assertNotIn(val_subject, train_subjects)
            self.assertNotEqual(test_subject, val_subject)
            self.assertEqual(len(train_subjects), 8)
            self.assertEqual(
                {str(record["subject_id"]).zfill(2) for record in fold_data["train_manifest"]},
                set(train_subjects),
            )
            self.assertEqual(
                {str(record["subject_id"]).zfill(2) for record in fold_data["val_manifest"]},
                {val_subject},
            )
            self.assertEqual(
                {str(record["subject_id"]).zfill(2) for record in fold_data["test_manifest"]},
                {test_subject},
            )

    def test_invalid_subject_count(self):
        records = [record for record in self.eligible_records if record["subject_id"] != "10"]
        with self.assertRaisesRegex(ValueError, "do not exactly match expected subjects"):
            generate_loso_splits(records, self.expected_subjects)

    def test_duplicate_sample_id(self):
        records = list(self.eligible_records)
        records.append(records[0])
        with self.assertRaisesRegex(ValueError, "Duplicate sample_id"):
            generate_loso_splits(records, self.expected_subjects)


if __name__ == "__main__":
    unittest.main()
