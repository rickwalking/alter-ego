"""Alembic revisions for the autopilot tables (AE-0350, AE-0357, AE-0361, AE-0369, AE-0370).

Proves the latest revision is the single head and that upgrade/downgrade apply
on a database stamped at the pre-autopilot head. The full chain from base is
PostgreSQL (an older revision uses ``ALTER COLUMN … TYPE``, which SQLite
rejects); CI's migration gate runs that chain.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_PREVIOUS_HEAD = "c9d0e1f2a3b4"
# AE-0378: the insights revision sits on top of AE-0377's POV thesis one.
_PARENT_HEAD = "b1c2d3e4f5a6"
_THIS_HEAD = "c2d3e4f5a6b7"
# AE-0393: the image bridge revision now sits on top of the insights one.
_SINGLE_HEAD = "d3e4f5a6b7c8"
# AE-0404: the audience-hours cache revision sits on top of the bridge one.
_AUDIENCE_HEAD = "a0e4f0a4b4c4"
# AE-0406: the pov_news quotes revision sits on top of the audience one.
_QUOTES_HEAD = "c4d5e6f7a8b9"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_TABLES = (
    "autopilot_runs",
    "topic_candidates",
    "integration_credentials",
    "telegram_updates",
    "autopilot_served_urls",
    "autopilot_x_signals",
    "instagram_manual_publishes",
    "autopilot_notify_cursor",
    # AE-0378: per-post Instagram insights snapshots.
    "instagram_post_insights",
    "instagram_stories",
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
    {"upgrade": command.upgrade, "downgrade": command.downgrade}[direction](
        cfg, revision
    )


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
    """``alembic heads`` is a single head that descends from the autopilot one."""
    _command, cfg, script_cls = _alembic_config()
    script = script_cls.from_config(cfg)
    assert list(script.get_heads()) == [_QUOTES_HEAD]
    quotes = script.get_revision(_QUOTES_HEAD)
    assert quotes is not None
    assert quotes.down_revision == _AUDIENCE_HEAD
    audience = script.get_revision(_AUDIENCE_HEAD)
    assert audience is not None
    assert audience.down_revision == _SINGLE_HEAD
    bridge = script.get_revision(_SINGLE_HEAD)
    assert bridge is not None
    assert bridge.down_revision == _THIS_HEAD
    revision = script.get_revision(_THIS_HEAD)
    assert revision is not None
    assert revision.down_revision == _PARENT_HEAD


def test_upgrade_and_downgrade_on_a_stamped_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upgrade from the pre-autopilot head creates the tables; downgrade drops them."""
    db_path = tmp_path / "autopilot.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
    conn.execute("CREATE TABLE carousel_creator_assets (id VARCHAR(36) PRIMARY KEY)")
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
    # AE-0361: image preset and guidance.
    assert {"image_style", "image_guidance"} <= topic_columns
    assert "signal_hash" in topic_columns
    # AE-0377: scout v3 mode and the draft / confirmed POV thesis.
    assert {"content_mode", "thesis_draft"} <= topic_columns
    assert "pov_thesis" in _columns(db_path, "autopilot_runs")
    run_columns = _columns(db_path, "autopilot_runs")
    assert "carousel_project_id" in run_columns
    assert "ig_post_id" in run_columns
    assert "ig_container_created_at" in run_columns
    assert "state" in _columns(db_path, "autopilot_runs")
    # QA r1 B3/H3/H4: split counters, queued rework, escalation version.
    for column in (
        "start_attempts",
        "rework_phase",
        "rework_feedback",
        "escalated_version",
        # AE-0370: the owner's publish time.
        "scheduled_at",
    ):
        assert column in run_columns
    manual_columns = _columns(db_path, "instagram_manual_publishes")
    assert {
        "carousel_project_id",
        "state",
        "ig_post_id",
        "claimed_at",
    } <= manual_columns
    # AE-0369: one Story row per carousel.
    assert {
        "carousel_project_id",
        "state",
        "story_container_id",
        "story_container_created_at",
        "story_media_id",
        "error",
    } <= _columns(db_path, "instagram_stories")
    signal_columns = _columns(db_path, "autopilot_x_signals")
    assert "source" in signal_columns
    assert "text" in signal_columns
    assert "posted_at" in signal_columns
    index_conn = sqlite3.connect(db_path)
    try:
        indexes = index_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'autopilot_runs'"
        ).fetchall()
    finally:
        index_conn.close()
    index_names = {row[0] for row in indexes}
    assert "idx_autopilot_runs_state_updated_at" in index_names
    assert "idx_autopilot_runs_state_scheduled_at" in index_names

    _run_migration("downgrade", _PREVIOUS_HEAD)

    remaining = _tables(db_path)
    for name in _TABLES:
        assert name not in remaining
    assert "carousel_projects" in remaining
