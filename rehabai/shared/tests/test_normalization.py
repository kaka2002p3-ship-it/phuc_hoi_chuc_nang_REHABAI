import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.generate_loso import hash_manifest
from shared.provenance import (
    VERIFICATION_KEY_ENV,
    build_provenance_record,
    verify_and_grant_real_verified,
)
from training.normalization import fit_fold_normalization

KEY = "normalization-test-key-at-least-32-bytes"


class TestNormalization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "source"
        self.processed_dir = self.root / "processed"
        self.source_dir.mkdir()
        self.processed_dir.mkdir()
        os.environ[VERIFICATION_KEY_ENV] = KEY
        self.train_manifest = []
        for index in range(1, 4):
            source = self.source_dir / f"sub01_vid{index}.mp4"
            processed = self.processed_dir / f"sub01_vid{index}.npz"
            source.write_bytes(f"video-{index}".encode("utf-8"))
            np.savez(processed, kinematics=np.ones((2, 12), dtype=np.float32) * index)
            candidate = build_provenance_record(
                str(source), "01", 1, 1.0, "success", "mediapipe-1.0",
                processed_path=str(processed), quality_gate_passed=True, compute_hash=True,
            )
            candidate["fold_id"] = "fold_01"
            candidate["split"] = "train"
            self.train_manifest.append(
                verify_and_grant_real_verified(
                    candidate, str(self.source_dir), str(self.processed_dir), KEY
                )
            )

    def tearDown(self):
        os.environ.pop(VERIFICATION_KEY_ENV, None)
        self.temp_dir.cleanup()

    def _metadata(self, records):
        return {
            "fold_id": "fold_01",
            "test_subject": "10",
            "validation_subjects": ["09"],
            "canonical_provenance_manifest_hash": hash_manifest(records),
            "canonical_train_manifest_hash": hash_manifest(records),
            "canonical_val_manifest_hash": "a" * 64,
            "canonical_test_manifest_hash": "b" * 64,
        }

    def test_fit_fold_normalization(self):
        output = self.root / "norm.json"
        schema = fit_fold_normalization(
            self.train_manifest,
            self._metadata(self.train_manifest),
            str(self.processed_dir),
            str(self.source_dir),
            str(output),
        )
        self.assertEqual(len(schema["kinematics"]["mean"]), 12)
        self.assertAlmostEqual(schema["kinematics"]["mean"][0], 2.0)
        self.assertTrue(output.exists())
        self.assertEqual(schema["metadata"]["sample_count"], 3)
        self.assertEqual(schema["metadata"]["frame_count"], 6)

    def test_missing_feature_fails_closed(self):
        records = list(self.train_manifest)
        (self.processed_dir / records[0]["sample_id"]).unlink()
        with self.assertRaisesRegex(ValueError, "processed feature"):
            fit_fold_normalization(
                records,
                self._metadata(records),
                str(self.processed_dir),
                str(self.source_dir),
                str(self.root / "norm.json"),
            )


if __name__ == "__main__":
    unittest.main()
