import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.models import ExtractedFact, Proposal, SourceReference


class ModelSerializationTests(unittest.TestCase):
    def test_source_reference_serializes_to_json_compatible_dict(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_meeting_minutes.md",
            document_title="Synthetic meeting minutes",
            location="page 1, paragraph 3",
            raw_evidence_text="Synthetic evidence text for validation.",
        )

        data = ref.to_dict()

        self.assertEqual(data["source_id"], "doc-001")
        self.assertEqual(data["source_path"], "samples/synthetic_meeting_minutes.md")
        self.assertEqual(data["document_title"], "Synthetic meeting minutes")
        self.assertEqual(data["location"], "page 1, paragraph 3")
        self.assertEqual(data["raw_evidence_text"], "Synthetic evidence text for validation.")
        json.dumps(data)

    def test_extracted_fact_without_source_refs_fails(self):
        with self.assertRaises(ValueError):
            ExtractedFact(
                fact_id="fact-001",
                fact_type="milestone",
                text="Synthetic milestone statement.",
                source_refs=[],
                confidence=0.8,
                extraction_method="unit-test",
            )

    def test_extracted_fact_without_evidence_text_or_location_fails(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_meeting_minutes.md",
        )

        with self.assertRaises(ValueError):
            ExtractedFact(
                fact_id="fact-001",
                fact_type="milestone",
                text="Synthetic milestone statement.",
                source_refs=[ref],
                confidence=0.8,
                extraction_method="unit-test",
            )

    def test_extracted_fact_accepts_model_raw_evidence_text(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_meeting_minutes.md",
        )

        fact = ExtractedFact(
            fact_id="fact-001",
            fact_type="milestone",
            text="Synthetic milestone statement.",
            source_refs=[ref],
            confidence=0.8,
            extraction_method="unit-test",
            raw_evidence_text="Synthetic evidence text for validation.",
        )

        self.assertEqual(fact.raw_evidence_text, "Synthetic evidence text for validation.")

    def test_extracted_fact_accepts_source_ref_location_as_evidence(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_meeting_minutes.md",
            location="page 1, paragraph 3",
        )

        fact = ExtractedFact(
            fact_id="fact-001",
            fact_type="milestone",
            text="Synthetic milestone statement.",
            source_refs=[ref],
            confidence=0.8,
            extraction_method="unit-test",
        )

        self.assertEqual(fact.source_refs[0].location, "page 1, paragraph 3")

    def test_extracted_fact_accepts_source_ref_raw_evidence_text(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_meeting_minutes.md",
            raw_evidence_text="Synthetic evidence text for validation.",
        )

        fact = ExtractedFact(
            fact_id="fact-001",
            fact_type="milestone",
            text="Synthetic milestone statement.",
            source_refs=[ref],
            confidence=0.8,
            extraction_method="unit-test",
        )

        self.assertEqual(fact.source_refs[0].raw_evidence_text, "Synthetic evidence text for validation.")

    def test_high_impact_proposal_types_require_review_by_default(self):
        ref = SourceReference(
            source_id="doc-001",
            source_path="samples/synthetic_contract_excerpt.md",
            location="section 1",
            raw_evidence_text="Synthetic clause evidence.",
        )
        proposal = Proposal(
            proposal_id="proposal-001",
            category="contract_obligation",
            title="Synthetic contract obligation update",
            proposed_change="Record a synthetic obligation for testing.",
            source_refs=[ref],
            confidence=0.9,
            extraction_method="unit-test",
        )

        self.assertTrue(proposal.requires_review)
        json.dumps(proposal.to_dict())


if __name__ == "__main__":
    unittest.main()
