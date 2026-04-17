"""Frozen write-surface schemas for the synthesis era.

These dataclasses are the **canonical payload contracts** that Phase 2
synthesis will persist. Freezing the shapes now — before synthesis is
built — lets every downstream layer (atomicity, supersession, domain
specialisation) be built on stable types rather than evolving ones.

Three shapes, all frozen:

- ``BoundedRecommendation`` — the final artefact a domain emits after
  synthesis fixes its action. Every per-domain recommendation class
  (starting with ``TrainingRecommendation`` in the recovery domain)
  must match this field set; subclasses may narrow ``action`` to an
  enum but may not add or remove fields. ``daily_plan_id`` is NULL
  pre-synthesis and NOT NULL after synthesis commits.

- ``DomainProposal`` — what a domain skill emits before synthesis
  reconciles. Deliberately omits ``follow_up`` (proposals don't
  schedule reviews — recommendations do) and any "mutation" field:
  skills do not own mutation logic, the runtime applies X-rule
  mutations mechanically. A proposal's ``daily_plan_id`` is always
  NULL at write time; synthesis assigns it.

- ``DailyPlan`` — the synthesis-run record that links N
  recommendations to their M input proposals and K X-rule firings.
  Idempotency key is ``(for_date, user_id)`` only — ``agent_version``
  is recorded per row but is NOT part of the uniqueness contract.
  ``superseded_by`` is the explicit opt-in to versioning, set only by
  ``hai synthesize --supersede``.

The helper ``canonical_daily_plan_id(for_date, user_id)`` derives the
stable key; synthesis uses it when replacing the canonical committed
plan atomically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal, Optional


Confidence = Literal["low", "moderate", "high"]
PolicyOutcome = Literal["allow", "soften", "block", "escalate"]


# ``BoundedRecommendation`` and ``DomainProposal`` both carry policy
# decisions; the shared shape lives here to avoid drift.
@dataclass(frozen=True)
class PolicyDecisionRecord:
    rule_id: str
    decision: PolicyOutcome
    note: str


@dataclass(frozen=True)
class FollowUpRecord:
    review_at: datetime
    review_question: str
    review_event_id: str


BOUNDED_RECOMMENDATION_FIELDS: tuple[str, ...] = (
    "schema_version",
    "recommendation_id",
    "user_id",
    "issued_at",
    "for_date",
    "action",
    "action_detail",
    "rationale",
    "confidence",
    "uncertainty",
    "follow_up",
    "policy_decisions",
    "bounded",
    "daily_plan_id",
    "domain",
)


DOMAIN_PROPOSAL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "proposal_id",
    "user_id",
    "for_date",
    "domain",
    "action",
    "action_detail",
    "rationale",
    "confidence",
    "uncertainty",
    "policy_decisions",
    "bounded",
    # Deliberately missing: follow_up (reviews schedule from recs, not
    # proposals), daily_plan_id (assigned by synthesis), any "mutation"
    # field (skills do not own mutation logic — runtime applies X-rules
    # mechanically per Codex round 2 boundary tightening).
)


DAILY_PLAN_FIELDS: tuple[str, ...] = (
    "daily_plan_id",
    "user_id",
    "for_date",
    "synthesized_at",
    "recommendation_ids",
    "proposal_ids",
    "x_rules_fired",
    "synthesis_meta",
    "superseded_by",
    "agent_version",
    # ``agent_version`` is intentionally recorded per row but NOT part
    # of the idempotency key — see ``canonical_daily_plan_id``.
)


@dataclass(frozen=True)
class BoundedRecommendation:
    """Canonical final artefact per domain after synthesis."""

    schema_version: str
    recommendation_id: str
    user_id: str
    issued_at: datetime
    for_date: date
    domain: str                                      # "recovery" | "running" | ...
    action: str                                      # subclasses narrow to a Literal enum
    action_detail: Optional[dict[str, Any]]
    rationale: tuple[str, ...]
    confidence: Confidence
    uncertainty: tuple[str, ...]
    follow_up: FollowUpRecord
    policy_decisions: tuple[PolicyDecisionRecord, ...]
    bounded: bool = True
    daily_plan_id: Optional[str] = None              # NULL pre-synthesis-commit, set after


@dataclass(frozen=True)
class DomainProposal:
    """Pre-synthesis payload emitted by a domain skill."""

    schema_version: str
    proposal_id: str
    user_id: str
    for_date: date
    domain: str
    action: str
    action_detail: Optional[dict[str, Any]]
    rationale: tuple[str, ...]
    confidence: Confidence
    uncertainty: tuple[str, ...]
    policy_decisions: tuple[PolicyDecisionRecord, ...]
    bounded: bool = True
    # Deliberate absence of follow_up + daily_plan_id + mutation fields.


@dataclass(frozen=True)
class DailyPlan:
    """Synthesis-run record linking proposals, firings, and recommendations."""

    daily_plan_id: str
    user_id: str
    for_date: date
    synthesized_at: datetime
    recommendation_ids: tuple[str, ...]
    proposal_ids: tuple[str, ...]
    x_rules_fired: tuple[str, ...]
    synthesis_meta: Optional[dict[str, Any]]
    agent_version: str                           # recorded per row, NOT part of idempotency key
    superseded_by: Optional[str] = None          # set only by `hai synthesize --supersede`


def canonical_daily_plan_id(for_date: date, user_id: str) -> str:
    """Return the stable canonical plan id for ``(for_date, user_id)``.

    Synthesis uses this id when replacing the canonical committed plan
    atomically. Changing the ``agent_version`` does not change this id;
    to produce a new plan alongside the old one, callers opt in via
    ``--supersede`` which assigns a fresh id with a ``_v<N>`` suffix.
    """

    return f"plan_{for_date.isoformat()}_{user_id}"
