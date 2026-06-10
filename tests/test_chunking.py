import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.chunking import chunk_extracted_document, chunk_extracted_documents
from hermes_compair.extract_text import extract_file


class ChunkingTests(unittest.TestCase):
    def test_chunk_source_references_preserve_file_lines_hash_and_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_notes.md"
            path.write_text(
                "# Synthetic notes\n\nLine three has project context.\nLine four continues it.\n",
                encoding="utf-8",
            )
            document = extract_file(path)

            chunks = chunk_extracted_document(document, max_lines=2)

            self.assertEqual(len(chunks), 2)
            first = chunks[0]
            self.assertEqual(first.document_id, document.document_id)
            self.assertEqual(first.text, "# Synthetic notes")
            self.assertEqual(first.metadata["source_file"], str(path))
            self.assertEqual(first.metadata["line_start"], 1)
            self.assertEqual(first.metadata["line_end"], 1)
            self.assertEqual(first.metadata["content_hash"], document.content_hash)
            self.assertEqual(first.metadata["extracted_at"], document.extracted_at.isoformat())
            self.assertEqual(first.metadata["extraction_method"], "text-like-utf-8")
            self.assertEqual(first.source_refs[0].source_path, str(path))
            self.assertEqual(first.source_refs[0].location, "lines 1-1")
            self.assertEqual(first.source_refs[0].content_hash, document.content_hash)
            self.assertEqual(first.source_refs[0].metadata["line_start"], 1)
            self.assertEqual(first.source_refs[0].metadata["line_end"], 1)
            self.assertEqual(first.source_refs[0].metadata["extraction_method"], "text-like-utf-8")
            self.assertEqual(first.source_refs[0].metadata["extracted_at"], document.extracted_at.isoformat())
            json.dumps(first.to_dict())

    def test_unsupported_documents_do_not_produce_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic_drawing.pdf"
            path.write_bytes(b"synthetic placeholder")
            document = extract_file(path)

            chunks = chunk_extracted_document(document)

            self.assertEqual(chunks, [])

    def test_chunk_extracted_documents_preserves_references_for_each_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.txt"
            second = root / "second.csv"
            first.write_text("Synthetic first note.\n", encoding="utf-8")
            second.write_text("heading,value\nsynthetic,1\n", encoding="utf-8")

            chunks = chunk_extracted_documents([extract_file(first), extract_file(second)])

            self.assertEqual(len(chunks), 2)
            self.assertEqual({chunk.metadata["source_file"] for chunk in chunks}, {str(first), str(second)})
            self.assertTrue(all(chunk.source_refs for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
