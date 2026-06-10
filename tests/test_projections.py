import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.models import Document, ExtractedFact, Proposal, SourceReference
from hermes_compair.projections import build_graph_projection, build_timeline_projection


def synthetic_ref():
    return SourceReference(
        source_id="synthetic-doc-001",
        source_path="samples/synthetic_project/meeting_minutes_001.md",
        document_title="Synthetic meeting minutes",
        location="line 12",
        raw_evidence_text="Synthetic evidence: Coordinator to submit mock shop drawing by 2026-07-15.",
    )


def synthetic_document():
    return Document(
        document_id="synthetic-doc-001",
        source_path="samples/synthetic_project/meeting_minutes_001.md",
        title="Synthetic meeting minutes",
        content_hash="synthetic-content-hash",
        document_type="meeting_minutes",
    )


def synthetic_action_fact():
    return ExtractedFact(
        fact_id="fact-action-001",
        fact_type="action_item",
        text="Coordinator to submit mock shop drawing by 2026-07-15.",
        source_refs=[synthetic_ref()],
        confidence=0.86,
        extraction_method="unit-test",
        raw_evidence_text="Coordinator to submit mock shop drawing by 2026-07-15.",
        attributes={
            "owner": "Synthetic Coordinator",
            "task": "submit mock shop drawing",
            "due_date_text": "2026-07-15",
        },
    )


def synthetic_deadline_proposal():
    return Proposal(
        proposal_id="proposal-deadline-001",
        category="deliverable_deadline",
        title="Review proposed deliverable deadline",
        proposed_change="Propose deadline for submit mock shop drawing by 2026-07-15.",
        source_refs=[synthetic_ref()],
        confidence=0.82,
        extraction_method="unit-test",
        review_status="pending_review",
        attributes={
            "previous_value": None,
            "proposed_value": {
                "task": "submit mock shop drawing",
                "owner": "Synthetic Coordinator",
                "due_date_text": "2026-07-15",
            },
            "source_fact_id": "fact-action-001",
            "status": "pending_review",
        },
    )


def synthetic_ref_without_raw_evidence():
    return SourceReference(
        source_id="synthetic-doc-001",
        source_path="samples/synthetic_project/meeting_minutes_001.md",
        document_title="Synthetic meeting minutes",
        location="line 12",
    )


def synthetic_action_fact_with_item_raw_evidence():
    return ExtractedFact(
        fact_id="fact-action-raw-001",
        fact_type="action_item",
        text="Coordinator to submit raw evidence drawing by 2026-07-15.",
        source_refs=[synthetic_ref_without_raw_evidence()],
        confidence=0.86,
        extraction_method="unit-test",
        raw_evidence_text="Item-level fact evidence text.",
        attributes={
            "owner": "Synthetic Coordinator",
            "task": "submit raw evidence drawing",
            "due_date_text": "2026-07-15",
        },
    )


def synthetic_deadline_proposal_with_item_raw_evidence():
    return Proposal(
        proposal_id="proposal-deadline-raw-001",
        category="deliverable_deadline",
        title="Review proposed raw evidence deadline",
        proposed_change="Propose deadline for raw evidence drawing by 2026-07-15.",
        source_refs=[synthetic_ref_without_raw_evidence()],
        confidence=0.82,
        extraction_method="unit-test",
        raw_evidence_text="Item-level proposal evidence text.",
        review_status="pending_review",
        attributes={
            "proposed_value": {
                "task": "submit raw evidence drawing",
                "due_date_text": "2026-07-15",
            },
            "source_fact_id": "fact-action-raw-001",
        },
    )


def node_types(projection):
    return {node["node_type"] for node in projection["nodes"]}


def edge_types(projection):
    return {edge["edge_type"] for edge in projection["edges"]}


class ProjectionBuilderTests(unittest.TestCase):
    def test_graph_projection_contains_cited_document_fact_owner_date_and_proposal_nodes(self):
        document = synthetic_document()
        fact = synthetic_action_fact()
        proposal = synthetic_deadline_proposal()

        projection = build_graph_projection([document], [fact], [proposal])

        self.assertEqual(
            node_types(projection),
            {"document", "action_item", "stakeholder", "date", "proposal"},
        )
        self.assertIn("document_contains_fact", edge_types(projection))
        self.assertIn("action_assigned_to", edge_types(projection))
        self.assertIn("action_due_on", edge_types(projection))
        self.assertIn("proposal_from_fact", edge_types(projection))
        self.assertTrue(all(edge["source_refs"] for edge in projection["edges"]))
        self.assertTrue(all(ref["source_path"].startswith("samples/synthetic_project/") for edge in projection["edges"] for ref in edge["source_refs"]))
        json.dumps(projection)

    def test_timeline_projection_contains_proposed_items_with_review_status_and_sources(self):
        proposal = synthetic_deadline_proposal()

        projection = build_timeline_projection([proposal])

        self.assertEqual(set(projection.keys()), {"items"})
        self.assertEqual(len(projection["items"]), 1)
        item = projection["items"][0]
        self.assertEqual(item["item_type"], "deliverable_deadline")
        self.assertEqual(item["title"], "submit mock shop drawing")
        self.assertEqual(item["date_text"], "2026-07-15")
        self.assertEqual(item["review_status"], "pending_review")
        self.assertTrue(item["source_refs"])
        self.assertEqual(item["source_refs"][0]["source_id"], "synthetic-doc-001")
        json.dumps(projection)

    def test_graph_projection_preserves_item_level_raw_evidence_on_nodes_and_edges(self):
        fact = synthetic_action_fact_with_item_raw_evidence()
        proposal = synthetic_deadline_proposal_with_item_raw_evidence()

        projection = build_graph_projection([synthetic_document()], [fact], [proposal])

        action_node = next(node for node in projection["nodes"] if node["node_id"] == "fact:fact-action-raw-001")
        proposal_node = next(node for node in projection["nodes"] if node["node_id"] == "proposal:proposal-deadline-raw-001")
        self.assertEqual(action_node["raw_evidence_text"], "Item-level fact evidence text.")
        self.assertEqual(proposal_node["raw_evidence_text"], "Item-level proposal evidence text.")

        document_edge = next(edge for edge in projection["edges"] if edge["edge_type"] == "document_contains_fact")
        proposal_edge = next(edge for edge in projection["edges"] if edge["edge_type"] == "proposal_from_fact")
        self.assertEqual(document_edge["raw_evidence_text"], "Item-level fact evidence text.")
        self.assertEqual(proposal_edge["raw_evidence_text"], "Item-level proposal evidence text.")

    def test_timeline_projection_preserves_item_level_raw_evidence(self):
        proposal = synthetic_deadline_proposal_with_item_raw_evidence()

        projection = build_timeline_projection([proposal])

        self.assertEqual(projection["items"][0]["raw_evidence_text"], "Item-level proposal evidence text.")

    def test_timeline_projection_skips_empty_proposal_ids(self):
        proposal = synthetic_deadline_proposal().to_dict()
        proposal["proposal_id"] = "   "

        projection = build_timeline_projection([proposal])

        self.assertEqual(projection, {"items": []})

    def test_timeline_projection_deep_copies_proposed_value(self):
        proposal = synthetic_deadline_proposal().to_dict()

        projection = build_timeline_projection([proposal])
        projection["items"][0]["attributes"]["proposed_value"]["owner"] = "Changed Owner"

        self.assertEqual(proposal["attributes"]["proposed_value"]["owner"], "Synthetic Coordinator")

    def test_projection_builders_do_not_mutate_input_dicts(self):
        documents = [synthetic_document().to_dict()]
        facts = [synthetic_action_fact().to_dict()]
        proposals = [synthetic_deadline_proposal().to_dict()]
        before = copy.deepcopy((documents, facts, proposals))

        build_graph_projection(documents, facts, proposals)
        build_timeline_projection(proposals)

        self.assertEqual((documents, facts, proposals), before)


if __name__ == "__main__":
    unittest.main()
