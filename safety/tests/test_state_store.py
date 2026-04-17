"""Tests for Phase 7A.1 — SQLite state store substrate.

Scope per the 7A.1 contract:
  - `hai state init` creates the DB file, applies migration 001, stamps
    schema_migrations.
  - `hai state migrate` is idempotent: re-running against a head DB applies
    nothing and leaves version untouched.
  - The bookkeeping table records every applied migration exactly once.
  - WAL mode + foreign keys are enabled on every new connection.

Out of scope (later phases): projection, dual-write, read CLIs, snapshot.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from health_agent_infra.cli import main as cli_main
from health_agent_infra.state import (
    apply_pending_migrations,
    current_schema_version,
    initialize_database,
    open_connection,
    resolve_db_path,
)


# ---------------------------------------------------------------------------
# resolve_db_path
# ---------------------------------------------------------------------------

def test_resolve_db_path_prefers_explicit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAI_STATE_DB", str(tmp_path / "env.db"))
    explicit = tmp_path / "explicit.db"
    assert resolve_db_path(explicit) == explicit


def test_resolve_db_path_honours_env_var(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HAI_STATE_DB", str(tmp_path / "env.db"))
    assert resolve_db_path() == tmp_path / "env.db"


def test_resolve_db_path_falls_back_to_platform_default(monkeypatch):
    monkeypatch.delenv("HAI_STATE_DB", raising=False)
    resolved = resolve_db_path()
    assert resolved.name == "state.db"
    assert "health_agent_infra" in resolved.parts


# ---------------------------------------------------------------------------
# initialize_database
# ---------------------------------------------------------------------------

def test_initialize_database_creates_file_and_applies_001(tmp_path: Path):
    db_path = tmp_path / "new.db"
    assert not db_path.exists()

    resolved, applied = initialize_database(db_path)

    assert resolved == db_path
    assert db_path.exists()
    assert len(applied) == 1
    version, filename = applied[0]
    assert version == 1
    assert filename == "001_initial.sql"


def test_initialize_database_creates_parent_dir_if_missing(tmp_path: Path):
    db_path = tmp_path / "nested" / "deep" / "state.db"
    assert not db_path.parent.exists()

    initialize_database(db_path)

    assert db_path.exists()


def test_initialize_database_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)
    _resolved, applied_again = initialize_database(db_path)
    assert applied_again == []


# ---------------------------------------------------------------------------
# Version bookkeeping
# ---------------------------------------------------------------------------

def test_schema_migrations_has_one_row_per_applied_migration(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT version, filename FROM schema_migrations ORDER BY version"
        ).fetchall()
    finally:
        conn.close()

    assert [tuple(r) for r in rows] == [(1, "001_initial.sql")]


def test_schema_migrations_not_duplicated_on_repeat_init(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)
    initialize_database(db_path)
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()["n"]
    finally:
        conn.close()

    assert count == 1


def test_current_schema_version_zero_on_empty_db(tmp_path: Path):
    db_path = tmp_path / "empty.db"
    conn = open_connection(db_path)
    try:
        assert current_schema_version(conn) == 0
    finally:
        conn.close()


def test_current_schema_version_matches_head_after_init(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        assert current_schema_version(conn) == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# apply_pending_migrations
# ---------------------------------------------------------------------------

def test_apply_pending_migrations_no_op_at_head(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        applied = apply_pending_migrations(conn)
    finally:
        conn.close()

    assert applied == []


def test_apply_pending_migrations_runs_001_on_empty_db(tmp_path: Path):
    db_path = tmp_path / "state.db"
    conn = open_connection(db_path)
    try:
        applied = apply_pending_migrations(conn)
    finally:
        conn.close()

    assert len(applied) == 1
    assert applied[0][0] == 1


# ---------------------------------------------------------------------------
# Pragmas — WAL + FKs
# ---------------------------------------------------------------------------

def test_open_connection_enables_wal(tmp_path: Path):
    db_path = tmp_path / "state.db"
    conn = open_connection(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode == "wal"


def test_open_connection_enables_foreign_keys(tmp_path: Path):
    db_path = tmp_path / "state.db"
    conn = open_connection(db_path)
    try:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        conn.close()
    assert fk == 1


# ---------------------------------------------------------------------------
# Schema presence — all expected tables from migration 001 exist
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    # bookkeeping
    "schema_migrations",
    # raw evidence
    "source_daily_garmin",
    "running_session",
    "gym_session",
    "gym_set",
    "nutrition_intake_raw",
    "stress_manual_raw",
    "context_note",
    # accepted state
    "accepted_recovery_state_daily",
    "accepted_running_state_daily",
    "accepted_resistance_training_state_daily",
    "accepted_nutrition_state_daily",
    "goal",
    # recommendation + review
    "recommendation_log",
    "review_event",
    "review_outcome",
}


def test_migration_001_creates_every_expected_table(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        conn.close()

    present = {r["name"] for r in rows}
    missing = EXPECTED_TABLES - present
    assert missing == set(), f"migration 001 failed to create: {sorted(missing)}"


# ---------------------------------------------------------------------------
# CLI smoke — `hai state init` / `hai state migrate`
# ---------------------------------------------------------------------------

def test_cli_state_init_creates_db_and_reports_applied(tmp_path: Path, capsys):
    db_path = tmp_path / "state.db"
    rc = cli_main(["state", "init", "--db-path", str(db_path)])
    assert rc == 0
    assert db_path.exists()

    out = capsys.readouterr().out
    import json
    payload = json.loads(out)
    assert payload["db_path"] == str(db_path)
    assert payload["created"] == [[1, "001_initial.sql"]]


def test_cli_state_migrate_on_head_db_reports_empty_applied(tmp_path: Path, capsys):
    db_path = tmp_path / "state.db"
    cli_main(["state", "init", "--db-path", str(db_path)])
    capsys.readouterr()  # discard init output

    rc = cli_main(["state", "migrate", "--db-path", str(db_path)])
    assert rc == 0

    import json
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version_before"] == 1
    assert payload["schema_version_after"] == 1
    assert payload["applied"] == []


def test_cli_state_migrate_fails_cleanly_when_db_missing(tmp_path: Path, capsys):
    db_path = tmp_path / "absent.db"
    rc = cli_main(["state", "migrate", "--db-path", str(db_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "state DB not found" in err


# ---------------------------------------------------------------------------
# Regression — foreign-key constraint actually bites when expected
# ---------------------------------------------------------------------------

def test_foreign_key_enforced_between_review_outcome_and_event(tmp_path: Path):
    db_path = tmp_path / "state.db"
    initialize_database(db_path)

    conn = open_connection(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO review_outcome "
                "(review_event_id, recommendation_id, user_id, recorded_at, "
                " followed_recommendation, source, ingest_actor, projected_at) "
                "VALUES ('rev_missing', 'rec_missing', 'u', "
                "        '2026-04-17T00:00:00Z', 1, 'claude_agent_v1', "
                "        'claude_agent_v1', '2026-04-17T00:00:00Z')"
            )
    finally:
        conn.close()
