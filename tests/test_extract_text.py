import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.extract_text import extract_file, extract_folder


class ExtractTextTests(unittest.TestCase):
    def test_markdown_extraction_preserves_line_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_minutes.md"
            path.write_text(
                "# Synthetic minutes\n\nDecision: use local parsing.\n",
                encoding="utf-8",
            )

            document = extract_file(path)

            self.assertTrue(document.supported)
            self.assertEqual(document.source_path, str(path))
            self.assertEqual(document.title, "synthetic_minutes.md")
            self.assertEqual(document.extraction_method, "text-like-utf-8")
            self.assertEqual(document.lines[0].line_number, 1)
            self.assertEqual(document.lines[0].text, "# Synthetic minutes")
            self.assertEqual(document.lines[1].line_number, 2)
            self.assertEqual(document.lines[1].text, "")
            self.assertEqual(document.lines[2].line_number, 3)
            self.assertEqual(document.lines[2].text, "Decision: use local parsing.")
            self.assertEqual(document.line_count, 3)
            self.assertIsNotNone(document.content_hash)
            self.assertIsNotNone(document.extracted_at)
            json.dumps(document.to_dict())

    def test_unsupported_file_is_marked_without_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_drawing.pdf"
            path.write_bytes(b"%PDF synthetic placeholder")

            document = extract_file(path)

            self.assertFalse(document.supported)
            self.assertEqual(document.source_path, str(path))
            self.assertEqual(document.extraction_method, "unsupported")
            self.assertEqual(document.lines, [])
            self.assertIn("unsupported", document.metadata["status"])
            json.dumps(document.to_dict())

    def test_extract_folder_includes_supported_and_unsupported_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_text("Synthetic note.\n", encoding="utf-8")
            (root / "drawing.pdf").write_bytes(b"synthetic placeholder")

            documents = extract_folder(root)

            self.assertEqual([Path(item.source_path).name for item in documents], ["drawing.pdf", "notes.txt"])
            self.assertEqual([item.supported for item in documents], [False, True])

    def test_symlink_file_is_rejected_before_reading_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "outside.txt"
            target.write_text("Synthetic target outside intended file.\n", encoding="utf-8")
            link = root / "linked.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlinks are not supported on this platform")

            with self.assertRaises(ValueError) as context:
                extract_file(link)

            self.assertIn("symlink", str(context.exception).lower())

    def test_invalid_utf8_file_is_marked_without_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.txt"
            path.write_bytes(b"\xff\xfe\x00")

            document = extract_file(path)

            self.assertFalse(document.supported)
            self.assertEqual(document.extraction_method, "unsupported")
            self.assertEqual(document.lines, [])
            self.assertIn("decode", document.metadata["status"])


if __name__ == "__main__":
    unittest.main()
