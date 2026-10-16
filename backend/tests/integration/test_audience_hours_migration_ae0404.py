"""Alembic revision for ``instagram_audience_hours`` (AE-0404).

Gherkin: tests/features/telegram_schedule_picker_ae0404.feature
  Scenario: An insights fetch error falls back silently (the daily cache table)

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

_REVISION = "a0e4f0a4b4c4"
_PARENT = "d3e4f5a6b7c8"
# AE-0406: the pov_news quotes revision is the single head on top of this one.
_HEAD = "c4d5e6f7a8b9"
_TABLE = "instagram_audience_hours"
_COLUMNS = {"ig_user_id", "online_followers", "checked_at", "fetched_at"}


def _stamped_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "audience_hours.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (_PARENT,))
    conn.commit()
    conn.close()
    return db_path


def _stamp(db_path: Path, revision: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE alembic_version SET version_num = ?", (revision,))
    conn.commit()
    conn.close()


def test_revision_is_the_single_head_on_top_of_the_bridge() -> None:
    """Chained on the AE-0393 image bridge revision; one head (AE-0406's)."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [_HEAD]
    assert script.get_revision(_HEAD).down_revision == _REVISION
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

    _run_migration("downgrade", _PARENT)
    assert _TABLE not in _tables(db_path)


def test_rerun_over_an_existing_or_missing_table_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Idempotent like AE-0371's: the backend may create the table at startup."""
    db_path = _stamped_db(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", _REVISION)
    _stamp(db_path, _PARENT)
    _run_migration("upgrade", _REVISION)
    assert _TABLE in _tables(db_path)

    _run_migration("downgrade", _PARENT)
    _stamp(db_path, _REVISION)
    _run_migration("downgrade", _PARENT)
    assert _TABLE not in _tables(db_path)
