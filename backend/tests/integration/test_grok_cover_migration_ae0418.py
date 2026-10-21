"""Alembic revision for the GrokBot cover (ADR-0024).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario Outline: A topic with a fresh cover is accepted in every mode

Upgrade/downgrade run on a SQLite file at the previous head; CI's migration
gate runs the full chain on Postgres. Idempotent: prod applies the SQL by hand.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.integration.test_autopilot_migration import (
    _alembic_config,
    _columns,
    _run_migration,
)

_REVISION = "d5e6f7a8b9c0"
_PARENT = "c4d5e6f7a8b9"
_COVERS = "autopilot_cover_assets"
_COLUMNS = (
    ("topic_candidates", "cover_asset_id"),
    ("autopilot_runs", "cover_chosen"),
    ("carousel_projects", "slide_cover"),
)


def test_revision_sits_on_top_of_the_quotes() -> None:
    # The single-head check moved to the newest revision's test (AE-0446).
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _stamped_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "cover.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (_PARENT,))
    conn.execute("CREATE TABLE topic_candidates (id CHAR(32) PRIMARY KEY)")
    conn.execute("CREATE TABLE autopilot_runs (id CHAR(32) PRIMARY KEY)")
    conn.execute("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE carousel_creator_assets (id VARCHAR(36) PRIMARY KEY)")
    conn.commit()
    conn.close()
    return db_path


def _tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    return {str(row[0]) for row in rows}


def _stamp(db_path: Path, revision: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE alembic_version SET version_num = ?", (revision,))
    conn.commit()
    conn.close()


def _assert_schema(db_path: Path, *, present: bool) -> None:
    assert (_COVERS in _tables(db_path)) is present
    for table, column in _COLUMNS:
        assert (column in _columns(db_path, table)) is present


def test_upgrade_adds_and_downgrade_drops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", _REVISION)
    _assert_schema(db_path, present=True)
    assert {"kind", "source_url", "topic_candidate_id"} <= _columns(db_path, _COVERS)
    _run_migration("downgrade", _PARENT)
    _assert_schema(db_path, present=False)


def test_rerun_over_existing_or_missing_schema_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", _REVISION)
    _stamp(db_path, _PARENT)
    _run_migration("upgrade", _REVISION)
    _assert_schema(db_path, present=True)
    _run_migration("downgrade", _PARENT)
    _stamp(db_path, _REVISION)
    _run_migration("downgrade", _PARENT)
    _assert_schema(db_path, present=False)
