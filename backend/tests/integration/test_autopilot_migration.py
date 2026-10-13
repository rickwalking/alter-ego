"""Alembic revision ``autopilot_tables`` (AE-0350).

Proves the new revision is the single head and that upgrade/downgrade apply
on a database stamped at the previous head. The full chain from base is
PostgreSQL (an older revision uses ``ALTER COLUMN … TYPE``, which SQLite
rejects); CI's migration gate runs that chain.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_PREVIOUS_HEAD = "c9d0e1f2a3b4"
_THIS_HEAD = "d0e1f2a3b4c5"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_TABLES = (
    "autopilot_runs",
    "topic_candidates",
    "integration_credentials",
    "telegram_updates",
)


def _alembic_config():
    """Import the alembic library, not the local ``backend/alembic`` folder."""
    saved = list(sys.path)
    sys.path = [entry for entry in sys.path if Path(entry).resolve() != _BACKEND_ROOT]
    sys.modules.pop("alembic", None)
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        from alembic import command
    finally:
        sys.path = saved
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return command, cfg, ScriptDirectory


def _run_migration(direction: str, revision: str) -> None:
    command, cfg, _script = _alembic_config()
    {"upgrade": command.upgrade, "downgrade": command.downgrade}[direction](cfg, revision)


def _tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def _columns(db_path: Path, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    finally:
        conn.close()
    return {row[1] for row in rows}


def test_autopilot_revision_is_the_only_head() -> None:
    """``alembic heads`` is exactly the autopilot revision."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [_THIS_HEAD]
    revision = script.get_revision(_THIS_HEAD)
    assert revision is not None
    assert revision.down_revision == _PREVIOUS_HEAD


def test_upgrade_and_downgrade_on_a_stamped_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Upgrade from the previous head creates the four tables; downgrade drops them."""
    db_path = tmp_path / "autopilot.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute(
        "INSERT INTO alembic_version (version_num) VALUES (?)",
        (_PREVIOUS_HEAD,),
    )
    conn.commit()
    conn.close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    _run_migration("upgrade", "head")

    present = _tables(db_path)
    for name in _TABLES:
        assert name in present
    topic_columns = _columns(db_path, "topic_candidates")
    assert "why_viral" in topic_columns
    assert "signal_hash" in topic_columns
    run_columns = _columns(db_path, "autopilot_runs")
    assert "carousel_project_id" in run_columns
    assert "ig_post_id" in run_columns
    assert "state" in _columns(db_path, "autopilot_runs")
    index_conn = sqlite3.connect(db_path)
    try:
        indexes = index_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'autopilot_runs'"
        ).fetchall()
    finally:
        index_conn.close()
    assert "idx_autopilot_runs_state_updated_at" in {row[0] for row in indexes}

    _run_migration("downgrade", _PREVIOUS_HEAD)

    remaining = _tables(db_path)
    for name in _TABLES:
        assert name not in remaining
    assert "carousel_projects" in remaining
