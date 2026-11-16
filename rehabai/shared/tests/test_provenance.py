import json
import os
import tempfile
import unittest
from pathlib import Path

from shared.provenance import (
    VERIFICATION_KEY_ENV,
    STATUS_MOCK,
    STATUS_REJECTED,
    STATUS_REAL_CANDIDATE,
    STATUS_REAL_VERIFIED,
    build_provenance_record,
    canonical_provenance_hash,
    check_eligibility,
    verify_and_grant_real_verified,
)

KEY = "provenance-test-key-at-least-32-bytes"


class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.video = self.root / "dummy.mp4"
        self.interim = self.root / "dummy_interim.npz"
        self.processed = self.root / "dummy_processed.npz"
        for path in (self.video, self.interim, self.processed):
            path.write_bytes(b"physical-test-file")
        os.environ[VERIFICATION_KEY_ENV] = KEY

    def tearDown(self):
        os.environ.pop(VERIFICATION_KEY_ENV, None)
        self.temp_dir.cleanup()

    def _record(self, extractor="MediaPipe Holistic 1.0.1", status="success", gate=True):
        return build_provenance_record(
            str(self.video), "01", 1, 1.0, status, extractor,
            interim_path=str(self.interim),
            processed_path=str(self.processed),
            quality_gate_passed=gate,
            compute_hash=True,
        )

    def test_mock_classification(self):
        self.assertEqual(self._record(extractor="MediaPipe Holistic 1.0.1 (Mock)")["data_status"], STATUS_MOCK)

    def test_rejected_classification(self):
        self.assertEqual(self._record(status="rejected_high_pose_missing", gate=False)["data_status"], STATUS_REJECTED)

    def test_candidate_classification(self):
        self.assertEqual(self._record()["data_status"], STATUS_REAL_CANDIDATE)

    def test_eligibility_requires_authorized_verification(self):
        candidate = self._record()
        eligible, reason = check_eligibility(candidate)
        self.assertFalse(eligible)
        self.assertIn("Invalid data_status", reason)

        forged = dict(candidate)
        forged["data_status"] = STATUS_REAL_VERIFIED
        forged["provenance_hash"] = canonical_provenance_hash(forged)
        eligible, reason = check_eligibility(forged)
        self.assertFalse(eligible)
        self.assertIn("verification_evidence", reason)

        verified = verify_and_grant_real_verified(candidate, str(self.root), str(self.root), KEY)
        eligible, reason = check_eligibility(verified, KEY)
        self.assertTrue(eligible, reason)

        evidence = json.loads(verified["verification_evidence"])
        evidence["verification_method"] = "forged"
        verified["verification_evidence"] = json.dumps(evidence, sort_keys=True)
        verified["provenance_hash"] = canonical_provenance_hash(verified)
        eligible, reason = check_eligibility(verified, KEY)
        self.assertFalse(eligible)
        self.assertIn("authority signature", reason)


if __name__ == "__main__":
    unittest.main()
