import ast
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.models import Chunk, Document, ExtractedFact, Proposal, SourceReference
from hermes_compair.storage import ProjectStore


class ProjectStoreTests(unittest.TestCase):
    def _source_ref(self):
        return SourceReference(
            source_id="synthetic-source-1",
            source_path="samples/synthetic_meeting_minutes.md",
            document_title="Synthetic meeting minutes",
            location="paragraph 2",
            raw_evidence_text="Synthetic evidence text.",
            content_hash="hash-source-1",
        )

    def _document(self, content_hash="hash-doc-1"):
        return Document(
            document_id="doc-synthetic-1",
            source_path="samples/synthetic_meeting_minutes.md",
            title="Synthetic meeting minutes",
            content_hash=content_hash,
            document_type="markdown",
            metadata={"synthetic": True},
        )

    def test_default_database_path_is_local_ignored_path(self):
        store = ProjectStore()

        self.assertEqual(store.db_path, Path(".hermes_compair/project_brain.db"))

    def test_schema_creates_mvp_and_projection_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "project.db")
            store.init_db()

            with sqlite3.connect(store.db_path) as connection:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
                    )
                }

            self.assertGreaterEqual(
                table_names,
                {
                    "documents",
                    "chunks",
                    "facts",
                    "proposals",
                    "graph_projection",
                    "timeline_projection",
                },
            )

    def test_document_upsert_is_idempotent_by_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "project.db")
            document = self._document()

            first = store.upsert_document(document)
            second = store.upsert_document(document)

            self.assertEqual(first, document.document_id)
            self.assertEqual(second, document.document_id)
            documents = store.list_documents()
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["document_id"], document.document_id)
            self.assertEqual(documents[0]["content_hash"], "hash-doc-1")
            json.dumps(documents)

    def test_chunk_fact_and_proposal_persistence_preserves_source_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "project.db")
            document = self._document()
            source_ref = self._source_ref()
            chunk = Chunk(
                chunk_id="chunk-synthetic-1",
                document_id=document.document_id,
                text="Synthetic paragraph about a proposed task.",
                source_refs=[source_ref],
                metadata={"chunk_index": 0},
            )
            fact = ExtractedFact(
                fact_id="fact-synthetic-1",
                fact_type="task_candidate",
                text="Synthetic team noted a task candidate.",
                source_refs=[source_ref],
                confidence=0.8,
                extraction_method="synthetic_test",
                raw_evidence_text="Synthetic evidence text.",
                attributes={"synthetic": True},
            )
            proposal = Proposal(
                proposal_id="proposal-synthetic-1",
                category="task_assignment",
                title="Review synthetic task",
                proposed_change="Add synthetic task for review.",
                source_refs=[source_ref],
                confidence=0.7,
                extraction_method="synthetic_test",
                raw_evidence_text="Synthetic evidence text.",
            )

            store.upsert_document(document)
            self.assertEqual(store.upsert_chunk(chunk), chunk.chunk_id)
            self.assertEqual(store.upsert_fact(fact), fact.fact_id)
            self.assertEqual(store.upsert_proposal(proposal), proposal.proposal_id)
            store.upsert_chunk(chunk)
            store.upsert_fact(fact)
            store.upsert_proposal(proposal)

            chunks = store.list_chunks(document_id=document.document_id)
            facts = store.list_facts(fact_type="task_candidate")
            proposals = store.list_proposals(review_status="pending")

            self.assertEqual(len(chunks), 1)
            self.assertEqual(len(facts), 1)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(chunks[0]["source_refs"][0]["location"], "paragraph 2")
            self.assertEqual(facts[0]["source_refs"][0]["raw_evidence_text"], "Synthetic evidence text.")
            self.assertEqual(proposals[0]["source_refs"][0]["source_path"], "samples/synthetic_meeting_minutes.md")
            self.assertTrue(proposals[0]["requires_review"])
            json.dumps({"chunks": chunks, "facts": facts, "proposals": proposals})

    def test_queries_are_parameterized_and_do_not_format_sql_strings(self):
        storage_path = ROOT / "src" / "hermes_compair" / "storage.py"
        source = storage_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        sql_calls = {
            "execute",
            "executemany",
            "executescript",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in sql_calls and node.args:
                    first_arg = node.args[0]
                    self.assertNotIsInstance(first_arg, ast.JoinedStr)
                    self.assertNotIsInstance(first_arg, ast.BinOp)
                    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                        self.assertNotIn("{", first_arg.value)

        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp) / "project.db")
            injected_type = "task_candidate' OR 1=1 --"
            store.upsert_document(self._document())
            store.upsert_fact(
                ExtractedFact(
                    fact_id="fact-safe-1",
                    fact_type=injected_type,
                    text="Synthetic injection-like text is stored as data.",
                    source_refs=[self._source_ref()],
                    confidence=0.6,
                    extraction_method="synthetic_test",
                    raw_evidence_text="Synthetic evidence text.",
                )
            )

            self.assertEqual(len(store.list_facts(fact_type="task_candidate")), 0)
            self.assertEqual(len(store.list_facts(fact_type=injected_type)), 1)


if __name__ == "__main__":
    unittest.main()
