"""AE-0371 migrations are idempotent (PR #106 review, item 2).

Gherkin: tests/features/carousel_content_mode.feature
("Re-running the AE-0371 migrations on a database that already has them").
Prod has no ``alembic_version`` table and the additive SQL was applied by hand,
so ``b0c1d2e3f4a5``, ``b1c2d3e4f5a6`` and ``c2d3e4f5a6b7`` must upgrade over
existing columns / tables and downgrade over missing ones without error.
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
_HEAD = "c2d3e4f5a6b7"
_INSIGHTS = "instagram_post_insights"
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


def test_fresh_upgrade_creates_the_pov_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: a fresh upgrade still adds every AE-0371 column and table."""
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", "head")

    _assert_pov_schema(db_path)


def test_upgrade_twice_over_hand_applied_sql_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: the columns and table already exist (prod) → upgrade does not fail."""
    db_path = _db_at_pre_autopilot(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", "head")

    # Prod state: schema already has everything, but alembic thinks it's before AE-0371.
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
    assert not _POV_ASSET_COLUMNS & _columns(db_path, "carousel_creator_assets")
    assert "pov_thesis" not in _columns(db_path, "autopilot_runs")
    assert "id" in _columns(db_path, "carousel_projects")
