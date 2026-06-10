import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.models import ExtractedFact, SourceReference
from hermes_compair.proposals import apply_proposal, create_proposals_from_facts


def synthetic_ref():
    return SourceReference(
        source_id="synthetic-doc-001",
        source_path="samples/synthetic_meeting_minutes.md",
        location="line 7",
        raw_evidence_text="Synthetic evidence for proposal tests.",
    )


def synthetic_fact(fact_type, text, attributes=None, confidence=0.8):
    return ExtractedFact(
        fact_id=f"fact-{fact_type}",
        fact_type=fact_type,
        text=text,
        source_refs=[synthetic_ref()],
        confidence=confidence,
        extraction_method="unit-test",
        raw_evidence_text=text,
        attributes=attributes or {},
    )


class ProposalCreationTests(unittest.TestCase):
    def test_deadline_proposal_requires_review(self):
        fact = synthetic_fact(
            "action_item",
            "Action item for Synthetic Coordinator to submit shop drawing by 2026-07-15.",
            {
                "owner": "Synthetic Coordinator",
                "task": "submit shop drawing",
                "due_date_text": "2026-07-15",
            },
        )

        proposals = create_proposals_from_facts([fact])

        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.category, "deliverable_deadline")
        self.assertTrue(proposal.requires_review)
        self.assertEqual(proposal.review_status, "pending_review")
        self.assertIsNone(proposal.attributes["previous_value"])
        self.assertEqual(proposal.attributes["proposed_value"]["due_date_text"], "2026-07-15")
        self.assertIn("submit shop drawing", proposal.attributes["rationale"])
        self.assertEqual(proposal.source_refs, fact.source_refs)
        self.assertEqual(proposal.confidence, fact.confidence)

    def test_contract_obligation_proposal_requires_review(self):
        fact = synthetic_fact(
            "obligation",
            "Synthetic contractor must maintain temporary weather protection.",
            {
                "obligated_party": "Synthetic contractor",
                "obligation_text": "maintain temporary weather protection",
            },
            confidence=0.74,
        )

        proposals = create_proposals_from_facts([fact])

        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.category, "contract_obligation")
        self.assertTrue(proposal.requires_review)
        self.assertEqual(proposal.review_status, "pending_review")
        self.assertIsNone(proposal.attributes["previous_value"])
        self.assertEqual(
            proposal.attributes["proposed_value"]["obligation_text"],
            "maintain temporary weather protection",
        )
        self.assertIn("source fact fact-obligation", proposal.attributes["rationale"])
        self.assertEqual(proposal.source_refs, fact.source_refs)

    def test_apply_proposal_has_no_silent_mutation_path(self):
        fact = synthetic_fact(
            "date_mention",
            "Date mentioned: 2026-08-01",
            {"date_text": "2026-08-01"},
        )
        proposal = create_proposals_from_facts([fact])[0]
        canonical_state = {"timeline": []}

        with self.assertRaisesRegex(NotImplementedError, "No direct apply path"):
            apply_proposal(proposal, canonical_state)

        self.assertEqual(canonical_state, {"timeline": []})


if __name__ == "__main__":
    unittest.main()
