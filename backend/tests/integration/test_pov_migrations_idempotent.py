"""The POV migrations are idempotent.

Gherkin: tests/features/carousel_content_mode.feature
("Re-running the POV migrations on a database that already has them").
Prod has no ``alembic_version`` table and the additive SQL was applied by hand,
so ``b0c1d2e3f4a5``, ``b1c2d3e4f5a6`` and ``c2d3e4f5a6b7`` must upgrade over
existing columns / tables and downgrade over missing ones without error.
The image bridge revision ``d3e4f5a6b7c8`` (``image_bridge_jobs``, also created at startup by
the backend) follows the same rule and is the head now.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.integration.test_autopilot_migration import (
    _columns,
    _run_migration,
    _tables,
)

_PRE_AUTOPILOT = "c9d0e1f2a3b4"
_PRE_POV = "a9b0c1d2e3f4"
_HEAD = "c4d5e6f7a8b9"
_INSIGHTS = "instagram_post_insights"
_BRIDGE_JOBS = "image_bridge_jobs"
_BRIDGE_INDEX = "ix_image_bridge_jobs_status_expires_at"
_POV_PROJECT_COLUMNS = {"content_mode", "hook_asset_id", "slide_count"}
_POV_ASSET_COLUMNS = {"role", "pose_tag"}
_POV_TOPIC_COLUMNS = {"content_mode", "thesis_draft"}


def _stamp(db_path: Path, revision: str) -> None:
    """Rewrite ``alembic_version`` without touching the schema (a hand-applied SQL)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE alembic_version SET version_num = ?", (revision,))
        conn.commit()
    finally:
        conn.close()


def _db_at_pre_autopilot(tmp_path: Path) -> Path:
    db_path = tmp_path / "idempotent.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE carousel_creator_assets (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute(
        "INSERT INTO alembic_version (version_num) VALUES (?)", (_PRE_AUTOPILOT,)
    )
    conn.commit()
    conn.close()
    return db_path


def _assert_pov_schema(db_path: Path) -> None:
    assert _columns(db_path, "carousel_projects") >= _POV_PROJECT_COLUMNS
    assert _columns(db_path, "carousel_creator_assets") >= _POV_ASSET_COLUMNS
    assert _columns(db_path, "topic_candidates") >= _POV_TOPIC_COLUMNS
    assert "pov_thesis" in _columns(db_path, "autopilot_runs")
    assert _INSIGHTS in _tables(db_path)
    assert _BRIDGE_JOBS in _tables(db_path)
    assert _BRIDGE_INDEX in _indexes(db_path, _BRIDGE_JOBS)


def _indexes(db_path: Path, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ?",
            (table,),
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def test_fresh_upgrade_creates_the_pov_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: a fresh upgrade still adds every POV column and table."""
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", "head")

    _assert_pov_schema(db_path)


def test_upgrade_twice_over_hand_applied_sql_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: the columns and table already exist (prod) → upgrade does not fail.

    Models the prod state: the schema already has everything, but alembic is stamped
    before the POV revision.
    """
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", "head")

    _stamp(db_path, _PRE_POV)
    _run_migration("upgrade", "head")
    _stamp(db_path, _PRE_POV)
    _run_migration("upgrade", "head")

    _assert_pov_schema(db_path)


def test_downgrade_over_missing_objects_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: downgrading twice (objects already gone) does not fail."""
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", "head")

    _run_migration("downgrade", _PRE_POV)
    _stamp(db_path, _HEAD)
    _run_migration("downgrade", _PRE_POV)

    assert _INSIGHTS not in _tables(db_path)
    assert _BRIDGE_JOBS not in _tables(db_path)
    assert not _POV_ASSET_COLUMNS & _columns(db_path, "carousel_creator_assets")
    assert "pov_thesis" not in _columns(db_path, "autopilot_runs")
    assert "id" in _columns(db_path, "carousel_projects")


def test_bridge_table_created_at_startup_is_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A table without its index (startup create_all) gets only the index."""
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", "head")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f"DROP INDEX {_BRIDGE_INDEX}")
        conn.commit()
    finally:
        conn.close()

    _stamp(db_path, "c2d3e4f5a6b7")
    _run_migration("upgrade", "head")

    assert _BRIDGE_INDEX in _indexes(db_path, _BRIDGE_JOBS)
