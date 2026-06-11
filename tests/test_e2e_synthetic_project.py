import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from hermes_compair.pipeline import run_local_pipeline
from hermes_compair.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from asgi_test_helper import request

SYNTHETIC_PROJECT = ROOT / "samples" / "synthetic_project"


class SyntheticProjectE2ETests(unittest.TestCase):
    def test_synthetic_project_pipeline_persists_cited_mvp_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "synthetic_project.db"

            result = run_local_pipeline(SYNTHETIC_PROJECT, db_path)

            store = ProjectStore(db_path)
            documents = store.list_documents()
            chunks = store.list_chunks()
            facts = store.list_facts()
            proposals = store.list_proposals()
            graph_nodes = store.list_graph_projection("node")
            graph_edges = store.list_graph_projection("edge")
            timeline_items = store.list_timeline_projection()

            self.assertEqual(result.db_path, db_path)
            self.assertGreaterEqual(len(documents), 3)
            self.assertGreater(len(chunks), 0)
            self.assertGreater(len(facts), 0)
            self.assertGreater(len(proposals), 0)
            self.assertGreater(len(graph_nodes), 0)
            self.assertGreater(len(graph_edges), 0)
            self.assertGreater(len(timeline_items), 0)

            for collection in (chunks, facts, proposals, graph_nodes, graph_edges, timeline_items):
                first = collection[0]
                self.assertIn("source_refs", first)
                self.assertTrue(first["source_refs"])
                source_ref = first["source_refs"][0]
                self.assertTrue(source_ref.get("source_id"))
                self.assertIn("samples/synthetic_project", source_ref.get("source_path", ""))

            for collection in (chunks, facts, proposals, graph_edges, timeline_items):
                source_ref = collection[0]["source_refs"][0]
                self.assertTrue(source_ref.get("location") or source_ref.get("raw_evidence_text"))

            self.assertTrue(any(item["item_type"] == "task_assignment" for item in timeline_items))
            self.assertTrue(all(proposal["requires_review"] for proposal in proposals))

            from hermes_compair.api import create_app

            app = create_app(db_path)
            dashboard_graph = request(app, "GET", "/graph").json()
            dashboard_timeline = request(app, "GET", "/timeline").json()
            self.assertGreater(len(dashboard_graph["nodes"]), 0)
            self.assertGreater(len(dashboard_graph["edges"]), 0)
            self.assertGreater(len(dashboard_timeline["items"]), 0)

    def test_pipeline_persisted_payloads_are_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path_a = Path(tmp) / "a.db"
            db_path_b = Path(tmp) / "b.db"

            run_local_pipeline(SYNTHETIC_PROJECT, db_path_a)
            run_local_pipeline(SYNTHETIC_PROJECT, db_path_b)

            self.assertEqual(_store_digest(ProjectStore(db_path_a)), _store_digest(ProjectStore(db_path_b)))

    def test_pipeline_replaces_previous_run_outputs_in_same_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_folder = Path(tmp) / "source"
            source_folder.mkdir()
            source_file = source_folder / "source.md"
            source_file.write_text("ACTION: Synthetic Owner - review mock item by 2026-07-01\n")
            db_path = Path(tmp) / "brain.db"

            run_local_pipeline(source_folder, db_path)
            source_file.unlink()
            run_local_pipeline(source_folder, db_path)

            store = ProjectStore(db_path)
            self.assertEqual(store.list_documents(), [])
            self.assertEqual(store.list_chunks(), [])
            self.assertEqual(store.list_facts(), [])
            self.assertEqual(store.list_proposals(), [])
            self.assertEqual(store.list_graph_projection(), [])
            self.assertEqual(store.list_timeline_projection(), [])

    def test_pipeline_rejects_database_path_inside_source_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_folder = Path(tmp) / "source"
            source_folder.mkdir()
            (source_folder / "source.md").write_text("ACTION: Synthetic Owner - review mock item by 2026-07-01\n")

            with self.assertRaisesRegex(ValueError, "outside the source folder"):
                run_local_pipeline(source_folder, source_folder / "brain")

            self.assertFalse((source_folder / "brain").exists())


def _store_digest(store: ProjectStore) -> str:
    payload = {
        "documents": store.list_documents(),
        "chunks": store.list_chunks(),
        "facts": store.list_facts(),
        "proposals": store.list_proposals(),
        "graph": store.list_graph_projection(),
        "timeline": store.list_timeline_projection(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if __name__ == "__main__":
    unittest.main()
