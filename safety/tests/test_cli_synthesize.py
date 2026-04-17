"""End-to-end tests for ``hai synthesize`` (Phase 2 step 4).

Covers the invariants called out in plan §4 deliverable 3:

1. **Atomicity** — a mid-synthesis failure rolls back every write. No
   orphan ``daily_plan`` with missing recommendations, no orphan
   ``x_rule_firing`` referencing a non-committed plan.
2. **Canonical idempotency** — re-running on the same
   ``(for_date, user_id)`` atomically replaces the prior plan (old
   firings + recommendations deleted; new ones inserted; counts stay
   coherent).
3. **Supersession** — ``--supersede`` keeps both plans addressable;
   prior plan's ``synthesis_meta_json`` carries a ``superseded_by``
   pointer to the new one; new plan has a fresh ``_v<N>`` id.
4. **X-rule end-to-end** — at least one Phase A rule firing is
   exercised end-to-end (snapshot → firing → mutation on draft →
   persisted x_rule_firing row with matching mutation_json).
"""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from health_agent_infra.core.schemas import canonical_daily_plan_id
from health_agent_infra.core.state import (
    initialize_database,
    open_connection,
    project_proposal,
)
from health_agent_infra.core.synthesis import (
    SynthesisError,
    run_synthesis,
)
from health_agent_infra.core.synthesis_policy import (
    XRuleFiring,
    XRuleWriteSurfaceViolation,
)
from health_agent_infra.core.writeback.proposal import (
    PROPOSAL_SCHEMA_VERSIONS,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic snapshot + proposals, single-running-domain v1
# ---------------------------------------------------------------------------

def _fresh_db(tmp_path) -> Path:
    db_path = tmp_path / "state.db"
    initialize_database(db_path)
    return db_path


def _running_proposal(**overrides):
    base = {
        "schema_version": PROPOSAL_SCHEMA_VERSIONS["running"],
        "proposal_id": "prop_2026-04-17_u_local_1_running_01",
        "user_id": "u_local_1",
        "for_date": "2026-04-17",
        "domain": "running",
        "action": "proceed_with_planned_run",
        "action_detail": None,
        "rationale": ["weekly_mileage_trend=moderate"],
        "confidence": "high",
        "uncertainty": [],
        "policy_decisions": [{"rule_id": "r1", "decision": "allow", "note": "full"}],
        "bounded": True,
    }
    base.update(overrides)
    return base


def _quiet_snapshot():
    """A snapshot that fires no X-rules — baseline for atomicity tests."""
    return {
        "recovery": {
            "classified_state": {"sleep_debt_band": "none"},
            "today": {
                "acwr_ratio": 1.0,
                "body_battery_end_of_day": 75,
                "all_day_stress": 25,
            },
        },
        "running": {},
    }


def _x1a_triggering_snapshot():
    """sleep_debt=moderate → X1a fires, softens running to easy aerobic."""
    return {
        "recovery": {
            "classified_state": {"sleep_debt_band": "moderate"},
            "today": {
                "acwr_ratio": 1.0,
                "body_battery_end_of_day": 75,
                "all_day_stress": 25,
            },
        },
        "running": {},
    }


def _insert_proposal(db_path: Path, proposal: dict):
    conn = open_connection(db_path)
    try:
        project_proposal(conn, proposal)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Happy path — synthesis commits a daily_plan + recommendation + links proposal
# ---------------------------------------------------------------------------

def test_synthesize_writes_daily_plan_and_recommendation_and_links_proposal(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    conn = open_connection(db_path)
    try:
        result = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_quiet_snapshot(),
        )
    finally:
        conn.close()

    assert result.daily_plan_id == canonical_daily_plan_id(date(2026, 4, 17), "u_local_1")
    assert result.recommendation_ids == ["rec_2026-04-17_u_local_1_running_01"]
    assert result.proposal_ids == [proposal["proposal_id"]]
    assert result.phase_a_firings == []
    assert result.phase_b_firings == []
    assert result.superseded_prior is None

    # Verify rows actually landed in the DB.
    conn = open_connection(db_path)
    try:
        plan_row = conn.execute(
            "SELECT * FROM daily_plan WHERE daily_plan_id = ?",
            (result.daily_plan_id,),
        ).fetchone()
        assert plan_row is not None
        assert plan_row["user_id"] == "u_local_1"
        assert plan_row["for_date"] == "2026-04-17"
        assert json.loads(plan_row["recommendation_ids_json"]) == result.recommendation_ids
        assert json.loads(plan_row["x_rules_fired_json"]) == []

        rec_row = conn.execute(
            "SELECT * FROM recommendation_log WHERE recommendation_id = ?",
            (result.recommendation_ids[0],),
        ).fetchone()
        assert rec_row is not None
        assert rec_row["domain"] == "running"
        assert rec_row["action"] == "proceed_with_planned_run"
        payload = json.loads(rec_row["payload_json"])
        assert payload["daily_plan_id"] == result.daily_plan_id
        assert payload["follow_up"]["review_event_id"].startswith("rev_")

        # Proposal now linked to plan.
        prop_row = conn.execute(
            "SELECT daily_plan_id FROM proposal_log WHERE proposal_id = ?",
            (proposal["proposal_id"],),
        ).fetchone()
        assert prop_row["daily_plan_id"] == result.daily_plan_id
    finally:
        conn.close()


def test_synthesize_refuses_when_no_proposals(tmp_path):
    db_path = _fresh_db(tmp_path)
    conn = open_connection(db_path)
    try:
        with pytest.raises(SynthesisError):
            run_synthesis(
                conn,
                for_date=date(2026, 4, 17),
                user_id="u_local_1",
                snapshot=_quiet_snapshot(),
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# X-rule end-to-end — X1a softens running proposal; firing persisted
# ---------------------------------------------------------------------------

def test_synthesize_x1a_firing_mutates_draft_and_persists_firing_row(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    conn = open_connection(db_path)
    try:
        result = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(),
        )

        assert [f.rule_id for f in result.phase_a_firings] == ["X1a"]

        rec_row = conn.execute(
            "SELECT action, payload_json FROM recommendation_log "
            "WHERE recommendation_id = ?",
            (result.recommendation_ids[0],),
        ).fetchone()
        # Phase A mutated the draft action from proceed → easy_aerobic.
        assert rec_row["action"] == "downgrade_to_easy_aerobic"
        payload = json.loads(rec_row["payload_json"])
        assert payload["action_detail"]["reason_token"] == "x1a_sleep_debt_trigger"

        firing_row = conn.execute(
            "SELECT x_rule_id, tier, affected_domain, mutation_json "
            "FROM x_rule_firing WHERE daily_plan_id = ?",
            (result.daily_plan_id,),
        ).fetchone()
        assert firing_row["x_rule_id"] == "X1a"
        assert firing_row["tier"] == "soften"
        assert firing_row["affected_domain"] == "running"
        mutation = json.loads(firing_row["mutation_json"])
        assert mutation["action"] == "downgrade_to_easy_aerobic"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Idempotency — canonical rerun replaces atomically
# ---------------------------------------------------------------------------

def test_synthesize_rerun_on_same_key_replaces_prior_plan(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    conn = open_connection(db_path)
    try:
        # First run: quiet snapshot → no firings.
        run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_quiet_snapshot(),
        )
        first_firing_count = conn.execute(
            "SELECT COUNT(*) AS c FROM x_rule_firing"
        ).fetchone()["c"]
        assert first_firing_count == 0

        # Second run: X1a snapshot → 1 firing.
        run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(),
        )

        plan_count = conn.execute(
            "SELECT COUNT(*) AS c FROM daily_plan "
            "WHERE for_date = ? AND user_id = ?",
            ("2026-04-17", "u_local_1"),
        ).fetchone()["c"]
        # Replacement, not duplication.
        assert plan_count == 1

        rec_count = conn.execute(
            "SELECT COUNT(*) AS c FROM recommendation_log "
            "WHERE for_date = ? AND user_id = ?",
            ("2026-04-17", "u_local_1"),
        ).fetchone()["c"]
        assert rec_count == 1

        firing_count = conn.execute(
            "SELECT COUNT(*) AS c FROM x_rule_firing"
        ).fetchone()["c"]
        # Prior plan's 0 firings replaced by the X1a firing.
        assert firing_count == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Supersession — --supersede keeps both plans addressable
# ---------------------------------------------------------------------------

def test_synthesize_supersede_preserves_prior_plan_and_flips_pointer(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    canonical = canonical_daily_plan_id(date(2026, 4, 17), "u_local_1")

    conn = open_connection(db_path)
    try:
        first = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_quiet_snapshot(),
        )
        assert first.daily_plan_id == canonical

        second = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(),
            supersede=True,
        )
        assert second.daily_plan_id == f"{canonical}_v2"
        assert second.superseded_prior == canonical

        # Both plan rows exist.
        plan_rows = conn.execute(
            "SELECT daily_plan_id, synthesis_meta_json FROM daily_plan "
            "WHERE for_date = ? AND user_id = ? "
            "ORDER BY daily_plan_id",
            ("2026-04-17", "u_local_1"),
        ).fetchall()
        assert [r["daily_plan_id"] for r in plan_rows] == [
            canonical, f"{canonical}_v2",
        ]

        # Prior plan's synthesis_meta_json now has superseded_by pointer.
        prior_meta = json.loads(plan_rows[0]["synthesis_meta_json"])
        assert prior_meta["superseded_by"] == f"{canonical}_v2"

        # Each plan's own recommendations exist separately.
        rec_count = conn.execute(
            "SELECT COUNT(*) AS c FROM recommendation_log "
            "WHERE for_date = ? AND user_id = ?",
            ("2026-04-17", "u_local_1"),
        ).fetchone()["c"]
        assert rec_count == 2
    finally:
        conn.close()


def test_synthesize_third_supersede_picks_v3(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    canonical = canonical_daily_plan_id(date(2026, 4, 17), "u_local_1")

    conn = open_connection(db_path)
    try:
        run_synthesis(
            conn, for_date=date(2026, 4, 17), user_id="u_local_1",
            snapshot=_quiet_snapshot(),
        )
        run_synthesis(
            conn, for_date=date(2026, 4, 17), user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(), supersede=True,
        )
        third = run_synthesis(
            conn, for_date=date(2026, 4, 17), user_id="u_local_1",
            snapshot=_quiet_snapshot(), supersede=True,
        )
        assert third.daily_plan_id == f"{canonical}_v3"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Atomicity — mid-synthesis failure leaves DB unchanged
# ---------------------------------------------------------------------------

def test_synthesize_atomicity_rolls_back_on_mid_write_failure(tmp_path, monkeypatch):
    """Simulate a failure mid-synthesis and verify nothing persists.

    We monkeypatch ``project_bounded_recommendation`` to raise after the
    daily_plan row was inserted and several x_rule_firing rows were
    inserted — the rollback must evict all of them.
    """

    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    from health_agent_infra.core import synthesis as synth_module

    real_fn = synth_module.project_bounded_recommendation

    def _fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated mid-write failure")

    monkeypatch.setattr(synth_module, "project_bounded_recommendation", _fail)

    conn = open_connection(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            run_synthesis(
                conn,
                for_date=date(2026, 4, 17),
                user_id="u_local_1",
                snapshot=_x1a_triggering_snapshot(),
            )

        plan_count = conn.execute(
            "SELECT COUNT(*) AS c FROM daily_plan"
        ).fetchone()["c"]
        assert plan_count == 0, "daily_plan row leaked past rollback"

        firing_count = conn.execute(
            "SELECT COUNT(*) AS c FROM x_rule_firing"
        ).fetchone()["c"]
        assert firing_count == 0, "x_rule_firing row leaked past rollback"

        rec_count = conn.execute(
            "SELECT COUNT(*) AS c FROM recommendation_log"
        ).fetchone()["c"]
        assert rec_count == 0, "recommendation_log row leaked past rollback"

        prop_row = conn.execute(
            "SELECT daily_plan_id FROM proposal_log WHERE proposal_id = ?",
            (proposal["proposal_id"],),
        ).fetchone()
        assert prop_row["daily_plan_id"] is None, (
            "proposal_log.daily_plan_id leaked past rollback"
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Skill overlay — rationale + uncertainty + review_question flow through
# ---------------------------------------------------------------------------

def test_synthesize_applies_skill_drafts_overlay(tmp_path):
    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    skill_drafts = [
        {
            "recommendation_id": "rec_2026-04-17_u_local_1_running_01",
            "rationale": ["composed_by_skill", "x1a_sleep_debt_moderate"],
            "uncertainty": ["sleep_capped_confidence"],
            "follow_up": {"review_question": "Did the easy run help?"},
        },
    ]

    conn = open_connection(db_path)
    try:
        result = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(),
            skill_drafts=skill_drafts,
        )

        rec_row = conn.execute(
            "SELECT payload_json FROM recommendation_log "
            "WHERE recommendation_id = ?",
            (result.recommendation_ids[0],),
        ).fetchone()
        payload = json.loads(rec_row["payload_json"])
        assert payload["rationale"] == [
            "composed_by_skill", "x1a_sleep_debt_moderate",
        ]
        assert payload["uncertainty"] == ["sleep_capped_confidence"]
        assert payload["follow_up"]["review_question"] == "Did the easy run help?"
    finally:
        conn.close()


def test_synthesize_ignores_skill_attempt_to_change_action(tmp_path):
    """Skill cannot override Phase A outcomes. Action is runtime-owned."""

    db_path = _fresh_db(tmp_path)
    proposal = _running_proposal()
    _insert_proposal(db_path, proposal)

    skill_drafts = [
        {
            "recommendation_id": "rec_2026-04-17_u_local_1_running_01",
            # Skill tries to UN-soften the action. Runtime must ignore.
            "action": "proceed_with_planned_run",
            "action_detail": {"skill_injected": True},
            "confidence": "high",
            "rationale": ["skill_overlay"],
        },
    ]

    conn = open_connection(db_path)
    try:
        result = run_synthesis(
            conn,
            for_date=date(2026, 4, 17),
            user_id="u_local_1",
            snapshot=_x1a_triggering_snapshot(),
            skill_drafts=skill_drafts,
        )
        rec_row = conn.execute(
            "SELECT action, payload_json FROM recommendation_log "
            "WHERE recommendation_id = ?",
            (result.recommendation_ids[0],),
        ).fetchone()
        # Phase A's mutation stands; skill override silently ignored.
        assert rec_row["action"] == "downgrade_to_easy_aerobic"
        payload = json.loads(rec_row["payload_json"])
        assert "skill_injected" not in (payload.get("action_detail") or {})
        # But rationale overlay did land.
        assert payload["rationale"] == ["skill_overlay"]
    finally:
        conn.close()
