"""Alembic revision for the ``pov_news`` quote columns (AE-0406).

Gherkin: tests/features/autopilot_pov_news_ae0406.feature
  Scenario: The carousel is a POV deck with the news voice (the project stores
  the quotes and the topic's sources)

Upgrade/downgrade run on a SQLite file at the previous head; CI's migration
gate runs the full chain on Postgres.
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

_REVISION = "c4d5e6f7a8b9"
_PARENT = "a0e4f0a4b4c4"
_TOPICS = "topic_candidates"
_PROJECTS = "carousel_projects"
_PROJECT_COLUMNS = {"pov_quotes", "pov_sources"}


def test_revision_is_the_single_head_on_top_of_the_audience_hours() -> None:
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT


def _stamped_db(tmp_path: Path) -> Path:
    """The two tables as they are before this revision, stamped at the parent."""
    db_path = tmp_path / "pov_news.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (_PARENT,))
    conn.execute("CREATE TABLE topic_candidates (id TEXT, content_mode VARCHAR(20))")
    conn.execute("CREATE TABLE carousel_projects (id TEXT, content_mode VARCHAR(20))")
    conn.commit()
    conn.close()
    return db_path


def _stamp(db_path: Path, revision: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE alembic_version SET version_num = ?", (revision,))
    conn.commit()
    conn.close()


def _assert_columns(db_path: Path, *, present: bool) -> None:
    assert ("quotes" in _columns(db_path, _TOPICS)) is present
    assert (_columns(db_path, _PROJECTS) >= _PROJECT_COLUMNS) is present
    assert not _PROJECT_COLUMNS & _columns(db_path, _PROJECTS) or present


def test_upgrade_adds_and_downgrade_drops_the_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", _REVISION)
    _assert_columns(db_path, present=True)
    assert "content_mode" in _columns(db_path, _PROJECTS)

    _run_migration("downgrade", _PARENT)
    _assert_columns(db_path, present=False)


def test_rerun_over_existing_or_missing_columns_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idempotent like AE-0371's: prod applies the SQL by hand."""
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", _REVISION)
    _stamp(db_path, _PARENT)
    _run_migration("upgrade", _REVISION)
    _assert_columns(db_path, present=True)

    _run_migration("downgrade", _PARENT)
    _stamp(db_path, _REVISION)
    _run_migration("downgrade", _PARENT)
    _assert_columns(db_path, present=False)
