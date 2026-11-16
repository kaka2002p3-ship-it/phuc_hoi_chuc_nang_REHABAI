import tempfile
import unittest
from pathlib import Path

from scripts.evaluate import run_evaluation


class TestEvaluation(unittest.TestCase):
    def test_missing_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-evaluation.json"
            with self.assertRaisesRegex(FileNotFoundError, "Config file not found"):
                run_evaluation(str(missing))


if __name__ == "__main__":
    unittest.main()
