import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from asgi_test_helper import request
from hermes_compair.api import create_app
from hermes_compair.models import Chunk, Document, ExtractedFact, Proposal, SourceReference
from hermes_compair.storage import ProjectStore


class ReadOnlyApiTests(unittest.TestCase):
    def test_health_reports_read_only_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp) / "project.db")
            response = request(app, "GET", "/health")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "read_only": True})

    def test_documents_endpoint_returns_stored_documents_without_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "project.db"
            store = ProjectStore(db_path)
            store.upsert_document(
                Document(
                    document_id="synthetic-doc-001",
                    source_path=str(Path(tmp) / "confidential" / "synthetic_minutes.md"),
                    title="Synthetic meeting minutes",
                    content_hash="synthetic-hash-001",
                    document_type="meeting_minutes",
                    metadata={"synthetic": True},
                )
            )
            app = create_app(db_path)
            response = request(app, "GET", "/documents")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload["documents"]), 1)
            document = payload["documents"][0]
            self.assertEqual(document["document_id"], "synthetic-doc-001")
            self.assertEqual(document["source_path"], "synthetic_minutes.md")
            self.assertNotIn(str(tmp), str(payload))

    def test_chunk_search_returns_matching_cited_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "project.db"
            source_ref = SourceReference(
                source_id="synthetic-doc-001",
                source_path="samples/synthetic_project/meeting_minutes.md",
                document_title="Synthetic meeting minutes",
                location="line 8",
                raw_evidence_text="Synthetic evidence about concrete delivery.",
            )
            store = ProjectStore(db_path)
            store.upsert_document(
                Document(
                    document_id="synthetic-doc-001",
                    source_path="samples/synthetic_project/meeting_minutes.md",
                    title="Synthetic meeting minutes",
                    content_hash="synthetic-hash-001",
                    document_type="meeting_minutes",
                )
            )
            store.upsert_chunk(
                Chunk(
                    chunk_id="chunk-001",
                    document_id="synthetic-doc-001",
                    text="Synthetic concrete delivery is planned for Friday.",
                    source_refs=[source_ref],
                    metadata={"chunk_index": 0},
                )
            )
            app = create_app(db_path)
            response = request(app, "GET", "/chunks/search?q=CONCRETE")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["query"], "CONCRETE")
            self.assertEqual([chunk["chunk_id"] for chunk in payload["chunks"]], ["chunk-001"])
            self.assertEqual(
                payload["chunks"][0]["source_refs"][0]["source_path"],
                "samples/synthetic_project/meeting_minutes.md",
            )

    def test_graph_redacts_absolute_document_source_used_as_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "project.db"
            absolute_source = Path(tmp) / "confidential" / "untitled_minutes.md"
            store = ProjectStore(db_path)
            store.upsert_document(
                Document(
                    document_id="synthetic-doc-untitled",
                    source_path=str(absolute_source),
                    title="",
                    content_hash="synthetic-hash-untitled",
                    document_type="meeting_minutes",
                )
            )
            app = create_app(db_path)
            response = request(app, "GET", "/graph")

            self.assertEqual(response.status_code, 200)
            payload_text = str(response.json())
            self.assertIn("untitled_minutes.md", payload_text)
            self.assertNotIn(str(tmp), payload_text)

    def test_graph_timeline_and_proposals_are_read_only_cited_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "project.db"
            source_ref = SourceReference(
                source_id="synthetic-doc-001",
                source_path="samples/synthetic_project/meeting_minutes.md",
                document_title="Synthetic meeting minutes",
                location="line 11",
                raw_evidence_text="Synthetic Coordinator to submit mock drawing by 2026-07-15.",
            )
            store = ProjectStore(db_path)
            store.upsert_document(
                Document(
                    document_id="synthetic-doc-001",
                    source_path="samples/synthetic_project/meeting_minutes.md",
                    title="Synthetic meeting minutes",
                    content_hash="synthetic-hash-001",
                    document_type="meeting_minutes",
                )
            )
            store.upsert_fact(
                ExtractedFact(
                    fact_id="fact-action-001",
                    fact_type="action_item",
                    text="Synthetic Coordinator to submit mock drawing by 2026-07-15.",
                    source_refs=[source_ref],
                    confidence=0.86,
                    extraction_method="unit-test",
                    raw_evidence_text="Synthetic Coordinator to submit mock drawing by 2026-07-15.",
                    attributes={
                        "owner": "Synthetic Coordinator",
                        "task": "submit mock drawing",
                        "due_date_text": "2026-07-15",
                    },
                )
            )
            store.upsert_proposal(
                Proposal(
                    proposal_id="proposal-deadline-001",
                    category="deliverable_deadline",
                    title="Review proposed deliverable deadline",
                    proposed_change="Propose deadline for submit mock drawing by 2026-07-15.",
                    source_refs=[source_ref],
                    confidence=0.82,
                    extraction_method="unit-test",
                    review_status="pending_review",
                    attributes={
                        "proposed_value": {
                            "task": "submit mock drawing",
                            "due_date_text": "2026-07-15",
                        },
                        "source_fact_id": "fact-action-001",
                    },
                )
            )
            app = create_app(db_path)

            graph = request(app, "GET", "/graph")
            timeline = request(app, "GET", "/timeline")
            proposals = request(app, "GET", "/proposals")
            forbidden_post = request(app, "POST", "/proposals", json_body={"unsafe": True})

            self.assertEqual(graph.status_code, 200)
            self.assertEqual(timeline.status_code, 200)
            self.assertEqual(proposals.status_code, 200)
            self.assertEqual(forbidden_post.status_code, 405)
            self.assertTrue(graph.json()["nodes"])
            self.assertEqual(timeline.json()["items"][0]["source_refs"][0]["source_id"], "synthetic-doc-001")
            self.assertTrue(proposals.json()["proposals"][0]["requires_review"])

    def test_chunk_search_requires_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(Path(tmp) / "project.db")
            response = request(app, "GET", "/chunks/search")

            self.assertEqual(response.status_code, 422)

    def test_empty_data_endpoint_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "missing" / "project.db"
            app = create_app(db_path)
            response = request(app, "GET", "/documents")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"documents": []})
            self.assertFalse(db_path.exists())


if __name__ == "__main__":
    unittest.main()
