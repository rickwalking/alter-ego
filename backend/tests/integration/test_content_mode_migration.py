"""Alembic revision for the carousel content mode (AE-0373).

Gherkin: tests/features/carousel_content_mode.feature (persistence background).
Upgrade adds the nullable POV columns and the creator-asset role/pose; downgrade
removes them and leaves the tables. Runs on SQLite from a stamped database (the
full chain from base is PostgreSQL-only; CI's migration gate runs it).
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

_REVISION = "b0c1d2e3f4a5"
_PARENT = "f8a9b0c1d2e3"
_PROJECT_COLUMNS = {
    "content_mode",
    "pov_thesis",
    "pov_personal_proof",
    "pov_format",
    "slide_count",
    "cta_goal",
    "hook_text",
    "hook_asset_id",
}
_ASSET_COLUMNS = {"role", "pose_tag"}


def _stamped_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "content_mode.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE carousel_creator_assets (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (_PARENT,))
    conn.commit()
    conn.close()
    return db_path


def test_revision_chains_on_the_story_revision() -> None:
    """The content-mode revision follows AE-0369's and is the single head."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == _PARENT
    assert list(script.get_heads()) == [_REVISION]


def test_upgrade_adds_and_downgrade_drops_the_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", _REVISION)
    assert _PROJECT_COLUMNS <= _columns(db_path, "carousel_projects")
    assert _ASSET_COLUMNS <= _columns(db_path, "carousel_creator_assets")

    _run_migration("downgrade", _PARENT)
    assert not _PROJECT_COLUMNS & _columns(db_path, "carousel_projects")
    assert not _ASSET_COLUMNS & _columns(db_path, "carousel_creator_assets")
    assert "id" in _columns(db_path, "carousel_projects")
