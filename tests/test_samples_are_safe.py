import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "samples" / "synthetic_project"
SAMPLE_FILES = [
    SAMPLE_DIR / "meeting_minutes_001.md",
    SAMPLE_DIR / "contract_excerpt_001.md",
    SAMPLE_DIR / "project_notes_001.md",
]
UNSAFE_MARKERS = [
    "password",
    "api_key",
    "secret",
]
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d .()/-]{7,}\d)(?!\d)")


class SyntheticSampleSafetyTests(unittest.TestCase):
    def test_expected_synthetic_sample_files_exist(self):
        missing = [path.relative_to(ROOT).as_posix() for path in SAMPLE_FILES if not path.exists()]
        self.assertEqual(missing, [])

    def test_samples_are_marked_synthetic(self):
        for path in SAMPLE_FILES:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("SYNTHETIC SAMPLE", text)
                self.assertIn("NOT REAL PROJECT DATA", text)

    def test_samples_do_not_contain_obvious_unsafe_markers(self):
        for path in SAMPLE_FILES:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                lowered = text.lower()
                for marker in UNSAFE_MARKERS:
                    self.assertNotIn(marker, lowered)
                self.assertIsNone(EMAIL_PATTERN.search(text))
                self.assertIsNone(PHONE_PATTERN.search(text))


if __name__ == "__main__":
    unittest.main()
