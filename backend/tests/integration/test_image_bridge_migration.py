"""Alembic revision for ``image_bridge_jobs`` (AE-0393).

Gherkin: tests/features/image_bridge.feature
  Scenario: The waiter works across processes (the table that carries the bytes)

Upgrade/downgrade run on a SQLite file stamped at the previous head; CI's
migration gate runs the full chain on Postgres.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.integration.test_autopilot_migration import (
    _alembic_config,
    _columns,
    _run_migration,
    _tables,
)

_REVISION = "d3e4f5a6b7c8"
_PARENT = "c2d3e4f5a6b7"
_TABLE = "image_bridge_jobs"
_INDEX = "ix_image_bridge_jobs_status_expires_at"
_COLUMNS = {
    "id",
    "status",
    "size",
    "token_sha256",
    "image_bytes",
    "error_code",
    "error_message",
    "created_at",
    "expires_at",
    "completed_at",
}


def _stamped_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "image_bridge.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (_PARENT,))
    conn.commit()
    conn.close()
    return db_path


def _indexes(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ?",
            (_TABLE,),
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def test_revision_is_chained_on_top_of_insights() -> None:
    """Chained on the AE-0378 insights revision; AE-0404's is the head now."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == ["a0e4f0a4b4c4"]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def test_upgrade_creates_and_downgrade_drops_the_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", _REVISION)

    assert _TABLE in _tables(db_path)
    assert _columns(db_path, _TABLE) == _COLUMNS
    assert _INDEX in _indexes(db_path)

    _run_migration("downgrade", _PARENT)

    assert _TABLE not in _tables(db_path)
