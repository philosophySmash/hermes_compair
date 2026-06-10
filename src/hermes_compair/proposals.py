"""Create human-reviewable proposals from cited extracted facts.

This module is intentionally read-only for the MVP. It converts extracted facts
into proposed updates and does not mutate canonical project state.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from hermes_compair.models import HIGH_IMPACT_PROPOSAL_CATEGORIES, ExtractedFact, Proposal

PROPOSAL_EXTRACTION_METHOD = "proposal-rules-v1"
PENDING_REVIEW_STATUS = "pending_review"


def create_proposals_from_facts(facts: Iterable[ExtractedFact]) -> list[Proposal]:
    """Convert cited extracted facts into proposed updates.

    Timeline, contract, task, payment, scope, safety, and liability-related facts
    are represented as proposals requiring review. No canonical state is changed.
    """

    proposals: list[Proposal] = []
    for fact in facts:
        proposal = _proposal_from_fact(fact)
        if proposal is not None:
            proposals.append(proposal)
    return proposals


def apply_proposal(proposal: Proposal, canonical_state: Any) -> None:
    """Reject direct proposal application in this MVP.

    The parameters are accepted to make attempted mutation paths explicit, but
    they are not read or changed.
    """

    raise NotImplementedError(
        "No direct apply path is available in this MVP. Proposals require human review before any canonical state change."
    )


def _proposal_from_fact(fact: ExtractedFact) -> Proposal | None:
    if fact.fact_type == "action_item":
        return _action_item_proposal(fact)
    if fact.fact_type == "date_mention":
        return _date_mention_proposal(fact)
    if fact.fact_type == "obligation":
        return _obligation_proposal(fact)
    return None


def _action_item_proposal(fact: ExtractedFact) -> Proposal:
    owner = _string_attribute(fact, "owner")
    task = _string_attribute(fact, "task") or fact.text
    due_date_text = _string_attribute(fact, "due_date_text")

    if due_date_text:
        category = "deliverable_deadline"
        title = "Review proposed deliverable deadline"
        proposed_value = {
            "task": task,
            "owner": owner or None,
            "due_date_text": due_date_text,
        }
        proposed_change = f"Propose deadline for {task} by {due_date_text}."
    else:
        category = "task_assignment"
        title = "Review proposed task assignment"
        proposed_value = {
            "task": task,
            "owner": owner or None,
        }
        proposed_change = f"Propose task assignment for {task}."

    return _build_proposal(
        fact=fact,
        category=category,
        title=title,
        proposed_change=proposed_change,
        proposed_value=proposed_value,
        rationale=f"Converted action_item source fact {fact.fact_id} into a reviewable task or deadline proposal: {task}.",
    )


def _date_mention_proposal(fact: ExtractedFact) -> Proposal:
    date_text = _string_attribute(fact, "date_text") or fact.text
    return _build_proposal(
        fact=fact,
        category="milestone_date",
        title="Review proposed milestone date",
        proposed_change=f"Propose milestone date {date_text} for review.",
        proposed_value={"date_text": date_text, "source_text": fact.text},
        rationale=f"Converted date_mention source fact {fact.fact_id} into a reviewable milestone date proposal.",
    )


def _obligation_proposal(fact: ExtractedFact) -> Proposal:
    obligated_party = _string_attribute(fact, "obligated_party")
    obligation_text = _string_attribute(fact, "obligation_text") or fact.text
    proposed_value = {
        "obligation_text": obligation_text,
        "obligated_party": obligated_party or None,
    }
    return _build_proposal(
        fact=fact,
        category="contract_obligation",
        title="Review proposed contract obligation",
        proposed_change=f"Propose contract obligation for review: {obligation_text}.",
        proposed_value=proposed_value,
        rationale=f"Converted obligation source fact {fact.fact_id} into a reviewable contract obligation proposal.",
    )


def _build_proposal(
    *,
    fact: ExtractedFact,
    category: str,
    title: str,
    proposed_change: str,
    proposed_value: dict[str, Any],
    rationale: str,
) -> Proposal:
    requires_review = category in HIGH_IMPACT_PROPOSAL_CATEGORIES
    return Proposal(
        proposal_id=_stable_id("proposal", fact.fact_id, category, proposed_change),
        category=category,
        title=title,
        proposed_change=proposed_change,
        source_refs=list(fact.source_refs),
        confidence=fact.confidence,
        extraction_method=PROPOSAL_EXTRACTION_METHOD,
        requires_review=requires_review,
        extraction_notes=f"Created from extracted fact using {PROPOSAL_EXTRACTION_METHOD}.",
        raw_evidence_text=fact.raw_evidence_text,
        extracted_at=fact.extracted_at,
        review_status=PENDING_REVIEW_STATUS,
        attributes={
            "previous_value": None,
            "proposed_value": proposed_value,
            "rationale": rationale,
            "source_fact_id": fact.fact_id,
            "source_fact_type": fact.fact_type,
            "status": PENDING_REVIEW_STATUS,
        },
    )


def _string_attribute(fact: ExtractedFact, key: str) -> str:
    value = fact.attributes.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return f"{prefix}:{digest.hexdigest()}"
