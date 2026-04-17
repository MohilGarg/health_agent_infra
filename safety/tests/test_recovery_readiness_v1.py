"""Deterministic + contract tests for health_agent_infra.

Judgment (state classification, policy, recommendation shaping) has moved
to agent-owned skills under ``skills/``. These tests cover only what the
runtime owns:

- PULL — Garmin adapter contract + real-export shape.
- CLEAN — baseline computation, missingness propagation, raw-summary aggregation.
- WRITEBACK — schema validation at the tool boundary, idempotency, locality.
- REVIEW — event scheduling, outcome persistence, summary counts.
- SCHEMAS — round-trip integrity.

Behavioural scenario tests from the pre-skill era were removed in commit 3.
Evaluating the skill-driven recommendation layer is done outside CI by
capturing agent outputs against golden scenarios.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from health_agent_infra.clean import build_raw_summary, clean_inputs
from health_agent_infra.pull.garmin import (
    GarminRecoveryReadinessAdapter,
    load_recovery_readiness_inputs,
)
from health_agent_infra.pull.protocol import FlagshipPullAdapter
from health_agent_infra.review.outcomes import (
    record_review_outcome,
    schedule_review,
    summarize_review_history,
)
from health_agent_infra.schemas import (
    FollowUp,
    PolicyDecision,
    RECOMMENDATION_SCHEMA_VERSION,
    ReviewEvent,
    ReviewOutcome,
    TrainingRecommendation,
)
from health_agent_infra.writeback.recommendation import (
    ALLOWED_RELATIVE_ROOT,
    perform_writeback,
)


AS_OF = date(2026, 4, 16)
NOW = datetime(2026, 4, 16, 7, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# CLEAN
# ---------------------------------------------------------------------------

def _baseline_week_rhr(as_of: date, base_bpm: float = 50.0) -> list[dict]:
    """Return 14 days of trailing RHR records around a baseline."""

    out = []
    for i in range(14, 0, -1):
        d = (as_of.fromordinal(as_of.toordinal() - i)).isoformat()
        out.append({"date": d, "bpm": base_bpm, "record_id": f"rhr_{d}"})
    return out


def _baseline_week_hrv(as_of: date, base_ms: float = 50.0) -> list[dict]:
    out = []
    for i in range(14, 0, -1):
        d = (as_of.fromordinal(as_of.toordinal() - i)).isoformat()
        out.append({"date": d, "rmssd_ms": base_ms, "record_id": f"hrv_{d}"})
    return out


def test_clean_emits_evidence_fields_from_inputs():
    evidence = clean_inputs(
        user_id="u_1",
        as_of_date=AS_OF,
        garmin_sleep={"duration_hours": 8.0, "record_id": "s_1"},
        garmin_resting_hr_recent=[{"date": AS_OF.isoformat(), "bpm": 55.0, "record_id": "rhr_today"}],
        garmin_hrv_recent=[{"date": AS_OF.isoformat(), "rmssd_ms": 60.0, "record_id": "hrv_today"}],
        garmin_training_load_7d=[{"date": AS_OF.isoformat(), "load": 400.0}],
        manual_readiness={
            "submission_id": "m_1",
            "soreness": "low",
            "energy": "moderate",
            "planned_session_type": "moderate",
            "active_goal": "strength_block",
        },
    )
    assert evidence.sleep_hours == 8.0
    assert evidence.sleep_record_id == "s_1"
    assert evidence.resting_hr == 55.0
    assert evidence.hrv_ms == 60.0
    assert evidence.trailing_7d_training_load == 400.0
    assert evidence.soreness_self_report == "low"
    assert evidence.active_goal == "strength_block"


def test_clean_handles_missing_sleep():
    evidence = clean_inputs(
        user_id="u_1",
        as_of_date=AS_OF,
        garmin_sleep=None,
        garmin_resting_hr_recent=[],
        garmin_hrv_recent=[],
        garmin_training_load_7d=[],
        manual_readiness=None,
    )
    assert evidence.sleep_hours is None
    assert evidence.sleep_record_id is None


def test_raw_summary_emits_baselines_and_ratios():
    rhr_history = _baseline_week_rhr(AS_OF, base_bpm=50.0)
    rhr_history.append({"date": AS_OF.isoformat(), "bpm": 58.0, "record_id": "rhr_today"})

    summary = build_raw_summary(
        user_id="u_1",
        as_of_date=AS_OF,
        garmin_sleep={"duration_hours": 7.0, "record_id": "s"},
        garmin_resting_hr_recent=rhr_history,
        garmin_hrv_recent=_baseline_week_hrv(AS_OF),
        garmin_training_load_7d=[],
    )
    assert summary.resting_hr == 58.0
    assert summary.resting_hr_baseline == pytest.approx(50.0)
    assert summary.resting_hr_ratio_vs_baseline == pytest.approx(58.0 / 50.0)
    assert summary.coverage_rhr_fraction == pytest.approx(7 / 7)  # 7 trailing days + today fit the window


def test_raw_summary_counts_rhr_spike_days():
    """3 consecutive days including today at >= 1.15x baseline == 3 spike days."""

    as_of = date(2026, 4, 16)
    history = _baseline_week_rhr(as_of - __import__("datetime").timedelta(days=3), base_bpm=50.0)
    # Spike the 3 most recent days (today + 2 prior)
    for i in range(3):
        d = (as_of.fromordinal(as_of.toordinal() - i)).isoformat()
        history.append({"date": d, "bpm": 60.0, "record_id": f"spike_{d}"})

    summary = build_raw_summary(
        user_id="u_1",
        as_of_date=as_of,
        garmin_sleep=None,
        garmin_resting_hr_recent=history,
        garmin_hrv_recent=[],
        garmin_training_load_7d=[],
    )
    assert summary.resting_hr_spike_days == 3


# ---------------------------------------------------------------------------
# PULL
# ---------------------------------------------------------------------------

def test_garmin_adapter_reads_committed_export_and_emits_fixture_shape():
    as_of = date(2026, 4, 8)
    pull = load_recovery_readiness_inputs(as_of)

    assert set(pull.keys()) == {"sleep", "resting_hr", "hrv", "training_load"}
    assert pull["sleep"] is not None
    assert "duration_hours" in pull["sleep"]
    assert any(row["date"] == as_of.isoformat() for row in pull["resting_hr"])


def test_garmin_adapter_class_conforms_to_flagship_pull_protocol():
    adapter = GarminRecoveryReadinessAdapter()
    assert isinstance(adapter, FlagshipPullAdapter)
    assert adapter.source_name == "garmin"

    pull = adapter.load(date(2026, 4, 8))
    assert set(pull.keys()) == {"sleep", "resting_hr", "hrv", "training_load"}


# ---------------------------------------------------------------------------
# WRITEBACK — contract (schema validation) + idempotency + locality
# ---------------------------------------------------------------------------

def _sample_recommendation(user_id: str = "u_1") -> TrainingRecommendation:
    return TrainingRecommendation(
        schema_version=RECOMMENDATION_SCHEMA_VERSION,
        recommendation_id=f"rec_{AS_OF.isoformat()}_{user_id}_01",
        user_id=user_id,
        issued_at=NOW,
        for_date=AS_OF,
        action="proceed_with_planned_session",
        action_detail={"active_goal": "strength_block"},
        rationale=["sleep_debt=none", "active_goal=strength_block"],
        confidence="high",
        uncertainty=[],
        follow_up=FollowUp(
            review_at=NOW.replace(day=17),
            review_question="Did today's session feel appropriate?",
            review_event_id=f"rev_2026-04-17_{user_id}_rec_{AS_OF.isoformat()}_{user_id}_01",
        ),
        policy_decisions=[
            PolicyDecision(rule_id="require_min_coverage", decision="allow", note="coverage=full"),
        ],
        bounded=True,
    )


def test_writeback_is_idempotent(tmp_path: Path):
    base = tmp_path / ALLOWED_RELATIVE_ROOT
    rec = _sample_recommendation()

    first = perform_writeback(rec, base_dir=base, now=NOW)
    second = perform_writeback(rec, base_dir=base, now=NOW)

    assert first.recommendation_id == second.recommendation_id
    log = (base / "recommendation_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(log) == 1


def test_writeback_locality_enforced_outside_allowed_root(tmp_path: Path):
    bad_base = tmp_path / "not_the_allowed_root"
    rec = _sample_recommendation()
    with pytest.raises(ValueError):
        perform_writeback(rec, base_dir=bad_base, now=NOW)


def test_writeback_cli_shape_validation_rejects_missing_fields(tmp_path: Path):
    """The `hai writeback` contract: agent-produced JSON must include all
    required fields. Missing fields fail closed."""

    from health_agent_infra.cli import _recommendation_from_dict

    with pytest.raises(ValueError) as exc:
        _recommendation_from_dict({"schema_version": "x"})
    assert "missing required fields" in str(exc.value)


def test_writeback_cli_shape_validation_accepts_valid_json():
    from health_agent_infra.cli import _recommendation_from_dict

    rec = _sample_recommendation()
    rebuilt = _recommendation_from_dict(rec.to_dict())
    assert rebuilt.recommendation_id == rec.recommendation_id
    assert rebuilt.action == rec.action


# ---------------------------------------------------------------------------
# REVIEW
# ---------------------------------------------------------------------------

def test_schedule_and_record_review(tmp_path: Path):
    base = tmp_path / ALLOWED_RELATIVE_ROOT
    rec = _sample_recommendation()
    perform_writeback(rec, base_dir=base, now=NOW)

    event = schedule_review(rec, base_dir=base)
    assert event.review_event_id == rec.follow_up.review_event_id

    outcome = record_review_outcome(
        event,
        base_dir=base,
        followed_recommendation=True,
        self_reported_improvement=True,
        free_text="felt good",
        now=NOW,
    )
    assert outcome.followed_recommendation is True
    assert (base / "review_outcomes.jsonl").exists()


def test_summarize_review_history_on_empty_returns_zeroed_counts():
    summary = summarize_review_history([])
    assert summary == {
        "total": 0,
        "followed_improved": 0,
        "followed_no_change": 0,
        "followed_unknown": 0,
        "not_followed": 0,
    }


def test_summarize_review_history_counts_each_category():
    def _outcome(i: int, followed: bool, improvement) -> ReviewOutcome:
        return ReviewOutcome(
            review_event_id=f"rev_{i}",
            recommendation_id=f"rec_{i}",
            user_id="u_1",
            recorded_at=NOW,
            followed_recommendation=followed,
            self_reported_improvement=improvement,
        )

    outcomes = [
        _outcome(1, True, True),
        _outcome(2, True, True),
        _outcome(3, True, False),
        _outcome(4, True, None),
        _outcome(5, False, None),
    ]
    summary = summarize_review_history(outcomes)
    assert summary == {
        "total": 5,
        "followed_improved": 2,
        "followed_no_change": 1,
        "followed_unknown": 1,
        "not_followed": 1,
    }


# ---------------------------------------------------------------------------
# SCHEMAS — round-trip
# ---------------------------------------------------------------------------

def test_training_recommendation_round_trip():
    rec = _sample_recommendation()
    data = rec.to_dict()
    # Serialize to JSON and back — must not raise
    s = json.dumps(data, sort_keys=True)
    parsed = json.loads(s)
    assert parsed["action"] == "proceed_with_planned_session"
    assert parsed["policy_decisions"][0]["rule_id"] == "require_min_coverage"
