import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_compair.deterministic_extractors import extract_facts_from_chunks
from hermes_compair.models import Chunk, SourceReference


def synthetic_chunk(text, line_start=1, line_end=1):
    ref = SourceReference(
        source_id="synthetic-doc-001",
        source_path="samples/synthetic_meeting_minutes.md",
        document_title="Synthetic meeting minutes",
        location=f"lines {line_start}-{line_end}",
        raw_evidence_text=text,
        metadata={"line_start": line_start, "line_end": line_end},
    )
    return Chunk(
        chunk_id=f"chunk-{line_start}-{line_end}",
        document_id="synthetic-doc-001",
        text=text,
        source_refs=[ref],
        metadata={"line_start": line_start, "line_end": line_end},
    )


class DeterministicExtractorTests(unittest.TestCase):
    def test_extracts_explicit_action_item_with_cited_line_range(self):
        chunk = synthetic_chunk(
            "Synthetic meeting notes\nACTION: Team Alpha - prepare synthetic schedule by 2026-06-15\nClosing note",
            line_start=10,
            line_end=12,
        )

        facts = extract_facts_from_chunks([chunk])

        action_facts = [fact for fact in facts if fact.fact_type == "action_item"]
        self.assertEqual(len(action_facts), 1)
        fact = action_facts[0]
        self.assertEqual(fact.attributes["owner"], "Team Alpha")
        self.assertEqual(fact.attributes["task"], "prepare synthetic schedule")
        self.assertEqual(fact.attributes["due_date_text"], "2026-06-15")
        self.assertEqual(fact.raw_evidence_text, "ACTION: Team Alpha - prepare synthetic schedule by 2026-06-15")
        self.assertEqual(fact.source_refs[0].location, "lines 11-11")
        self.assertEqual(fact.source_refs[0].raw_evidence_text, fact.raw_evidence_text)
        self.assertFalse(fact.requires_review)
        self.assertLessEqual(fact.confidence, 0.85)
        json.dumps(fact.to_dict())

    def test_extracts_iso_and_written_date_mentions_with_evidence(self):
        chunk = synthetic_chunk(
            "Synthetic date list\nReview date: 2026-06-15\nWorkshop date: June 15, 2026\nInspection date: 15 June 2026",
            line_start=3,
            line_end=6,
        )

        facts = extract_facts_from_chunks([chunk])

        date_facts = [fact for fact in facts if fact.fact_type == "date_mention"]
        date_texts = [fact.attributes["date_text"] for fact in date_facts]
        self.assertEqual(date_texts, ["2026-06-15", "June 15, 2026", "15 June 2026"])
        self.assertTrue(all(fact.source_refs for fact in date_facts))
        self.assertEqual(date_facts[0].source_refs[0].location, "lines 4-4")
        self.assertEqual(date_facts[1].source_refs[0].location, "lines 5-5")
        self.assertEqual(date_facts[2].source_refs[0].location, "lines 6-6")
        self.assertTrue(all(fact.raw_evidence_text for fact in date_facts))
        self.assertTrue(all(fact.confidence <= 0.8 for fact in date_facts))

    def test_ambiguous_action_item_requires_review_without_hallucinated_owner_or_date(self):
        chunk = synthetic_chunk(
            "ACTION: - confirm synthetic access route by TBD\nACTION: Team Beta - finalize synthetic checklist",
            line_start=20,
            line_end=21,
        )

        facts = extract_facts_from_chunks([chunk])

        action_facts = [fact for fact in facts if fact.fact_type == "action_item"]
        self.assertEqual(len(action_facts), 2)
        missing_owner = action_facts[0]
        self.assertTrue(missing_owner.requires_review)
        self.assertEqual(missing_owner.attributes.get("owner"), "")
        self.assertEqual(missing_owner.attributes["task"], "confirm synthetic access route")
        self.assertEqual(missing_owner.attributes.get("due_date_text"), "TBD")
        self.assertLessEqual(missing_owner.confidence, 0.4)

        missing_date = action_facts[1]
        self.assertTrue(missing_date.requires_review)
        self.assertEqual(missing_date.attributes["owner"], "Team Beta")
        self.assertEqual(missing_date.attributes["task"], "finalize synthetic checklist")
        self.assertNotIn("due_date_text", missing_date.attributes)
        self.assertLessEqual(missing_date.confidence, 0.4)

    def test_ambiguous_owner_tokens_require_review_and_low_confidence(self):
        cases = ("TBD", "unknown")
        for owner in cases:
            with self.subTest(owner=owner):
                chunk = synthetic_chunk(
                    f"ACTION: {owner} - prepare synthetic report by 2026-06-15"
                )

                facts = extract_facts_from_chunks([chunk])

                action_facts = [fact for fact in facts if fact.fact_type == "action_item"]
                self.assertEqual(len(action_facts), 1)
                fact = action_facts[0]
                self.assertEqual(fact.attributes["owner"], owner)
                self.assertEqual(fact.attributes["task"], "prepare synthetic report")
                self.assertEqual(fact.attributes["due_date_text"], "2026-06-15")
                self.assertTrue(fact.requires_review)
                self.assertLessEqual(fact.confidence, 0.4)

    def test_does_not_extract_action_without_explicit_action_prefix(self):
        chunk = synthetic_chunk("Team Alpha should prepare synthetic schedule by 2026-06-15")

        facts = extract_facts_from_chunks([chunk])

        self.assertEqual([fact for fact in facts if fact.fact_type == "action_item"], [])


if __name__ == "__main__":
    unittest.main()
