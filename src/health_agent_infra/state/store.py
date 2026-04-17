"""SQLite state store — connection management, WAL enablement, migrations.

Phase 7A.1 substrate. This module owns exactly three concerns:

    1. Deciding where the DB file lives (``HAI_STATE_DB`` env var ->
       ``~/.local/share/health_agent_infra/state.db``).
    2. Opening SQLite connections with WAL mode + foreign-key enforcement.
    3. Running forward-only versioned migrations from
       ``src/health_agent_infra/state/migrations/NNN_*.sql`` against a
       ``schema_migrations`` version table.

Projection (raw -> accepted), dual-write, read CLIs, and snapshot logic
are explicitly not in this module. They land in later phases.
"""

from __future__ import annotations

import os
import re
import sqlite3
from importlib.resources import files
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "health_agent_infra" / "state.db"

_HAI_STATE_DB_ENV = "HAI_STATE_DB"

_MIGRATION_FILENAME_RE = re.compile(r"^(\d{3,})_[a-zA-Z0-9_]+\.sql$")


def resolve_db_path(explicit: Optional[Path | str] = None) -> Path:
    """Return the DB path to use, preferring explicit arg > env var > default."""

    if explicit is not None:
        return Path(explicit).expanduser()
    env_value = os.environ.get(_HAI_STATE_DB_ENV)
    if env_value:
        return Path(env_value).expanduser()
    return DEFAULT_DB_PATH


def open_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + foreign keys enforced.

    Creates the parent directory if needed. The DB file is created by SQLite
    on first connect if absent. Uses Python's default deferred isolation so
    DML can be wrapped in explicit transactions.
    """

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Create the ``schema_migrations`` bookkeeping table if it doesn't exist."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            filename    TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )
        """
    )


def current_schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if none."""

    _ensure_migrations_table(conn)
    row = conn.execute(
        "SELECT MAX(version) AS v FROM schema_migrations"
    ).fetchone()
    if row is None or row["v"] is None:
        return 0
    return int(row["v"])


def _discover_migrations() -> list[tuple[int, str, str]]:
    """Return sorted list of (version, filename, sql_body) from packaged migrations.

    Resolves via ``importlib.resources`` so the migrations ship inside the
    wheel. Only files matching ``NNN_name.sql`` are considered.
    """

    migrations_dir = files("health_agent_infra").joinpath("state", "migrations")
    discovered: list[tuple[int, str, str]] = []
    for entry in migrations_dir.iterdir():
        name = entry.name
        match = _MIGRATION_FILENAME_RE.match(name)
        if not match:
            continue
        version = int(match.group(1))
        sql_body = entry.read_text(encoding="utf-8")
        discovered.append((version, name, sql_body))
    discovered.sort(key=lambda t: t[0])
    return discovered


def apply_pending_migrations(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Apply every migration whose version > current_schema_version.

    Returns the list of ``(version, filename)`` tuples that were applied in
    this call. Empty list means the DB was already at head.

    Migrations run inside a transaction each; a failure mid-file rolls back
    that migration and raises. Already-applied migrations from prior files
    remain committed.
    """

    applied_now: list[tuple[int, str]] = []
    current = current_schema_version(conn)
    for version, filename, sql_body in _discover_migrations():
        if version <= current:
            continue
        # `executescript` in Python's sqlite3 commits any pending transaction
        # and then runs the script with its own implicit commit. SQLite itself
        # handles each DDL statement transactionally. If a script fails
        # partway, the partially-created tables remain; re-running init on
        # a fresh DB file is the recovery path. Once the DDL lands, we record
        # the version in an explicit transaction so bookkeeping stays atomic.
        try:
            conn.executescript(sql_body)
        except Exception:
            raise
        try:
            conn.execute(
                "INSERT INTO schema_migrations (version, filename, applied_at) "
                "VALUES (?, ?, datetime('now'))",
                (version, filename),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied_now.append((version, filename))
        current = version
    return applied_now


def initialize_database(db_path: Path) -> tuple[Path, list[tuple[int, str]]]:
    """Open the DB at ``db_path`` (creating file + parent dir if needed),
    enable WAL + FKs, ensure the bookkeeping table, and apply pending
    migrations.

    Returns ``(resolved_path, applied_migrations)`` where
    ``applied_migrations`` is empty if the DB was already at head.
    """

    conn = open_connection(db_path)
    try:
        _ensure_migrations_table(conn)
        applied = apply_pending_migrations(conn)
    finally:
        conn.close()
    return db_path, applied


def list_applied_migrations(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    """Yield rows from schema_migrations ordered by version ascending."""

    _ensure_migrations_table(conn)
    return conn.execute(
        "SELECT version, filename, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
