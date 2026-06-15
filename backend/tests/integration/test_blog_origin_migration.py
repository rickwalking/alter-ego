"""Migration tests for AE-0127 blog_post origin backfill (upgrade + downgrade).

Gherkin not applicable — this is a schema-migration safety net (DDL/data-movement),
not a behavioral scenario.

These tests run the REAL alembic migration ``b2c3d4e5f6a7`` against a temp SQLite
database and prove the additive backfill is reversible WITHOUT DATA LOSS:

* upgrade re-labels pre-existing project-linked rows to ``origin='carousel'`` and
  inserts one ``carousel-{id}`` row per eligible carousel project;
* downgrade deletes ONLY the inserted ``carousel-{id}`` rows and preserves the
  pre-existing project-linked rows (a naive ``DELETE WHERE origin='carousel'``
  would destroy them — the regression this test guards).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_PRE_REV = "a1b2c3d4e5f6"
_ORIGIN_REV = "b2c3d4e5f6a7"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_EXISTING_BLOG_ID = "existing-blog-1"
_EXISTING_PROJECT_ID = "project-existing-1"
_EXISTING_SLUG = "my-handwritten-post"  # NOT a carousel-* slug
_CAROUSEL_PROJECT_ID = "project-carousel-1"


def _run_migration(direction: str, revision: str) -> None:
    """Drive the real alembic migration via its in-process API (no subprocess).

    The local ``backend/alembic/`` migrations package shadows the installed
    alembic library on sys.path under pytest, so the library is imported with the
    backend root temporarily dropped from sys.path. The DB URL is read from the
    ``DATABASE_URL`` env var the caller sets (per-test temp SQLite file).
    """
    saved = list(sys.path)
    sys.path = [p for p in sys.path if Path(p).resolve() != _BACKEND_ROOT]
    sys.modules.pop("alembic", None)
    try:
        from alembic.config import Config

        from alembic import command
    finally:
        sys.path = saved
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    {"upgrade": command.upgrade, "downgrade": command.downgrade}[direction](
        cfg, revision
    )


def _seed_pre_origin_rows(db_path: str) -> None:
    """Insert a pre-existing project-linked blog post + an eligible carousel."""
    conn = sqlite3.connect(db_path)
    try:
        empty_json = "[]"
        conn.execute(
            """
            INSERT INTO blog_posts (
                id, project_id, title, slug, status, content,
                editor_comments, version_history, sources, citations,
                ai_suggestions, ai_generation_metadata, keywords,
                view_count, like_count, comment_count, share_count, lock_version,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 1,
                      datetime('now'), datetime('now'))
            """,
            (
                _EXISTING_BLOG_ID,
                _EXISTING_PROJECT_ID,
                "Pre-existing handwritten post",
                _EXISTING_SLUG,
                "published",
                "{}",
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                "{}",
                empty_json,
            ),
        )
        conn.execute(
            """
            INSERT INTO carousel_projects (
                id, is_public, topic, audience, niche, slides_config,
                aspect_ratio, language, generate_images, image_model, image_style,
                theme, status, workflow_status, lock_version, blog_markdown,
                created_at, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, 0, 'gemini', 'comic_neon',
                      'default', 'completed', 'completed', 1, ?,
                      datetime('now'), datetime('now'))
            """,
            (
                _CAROUSEL_PROJECT_ID,
                "AI",
                "devs",
                "tech",
                "6",
                "1:1",
                "en",
                "# Carousel blog body",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _origins_by_slug(db_path: str) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        return dict(conn.execute("SELECT slug, origin FROM blog_posts").fetchall())
    finally:
        conn.close()


def _slugs(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT slug FROM blog_posts")}
    finally:
        conn.close()


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A temp DB upgraded to the pre-origin revision with seeded rows."""
    db_path = str(tmp_path / "origin_migration.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", _PRE_REV)
    _seed_pre_origin_rows(db_path)
    return db_path


# Scenario: upgrade re-labels existing rows and inserts carousel-derived rows.
def test_upgrade_relabels_existing_and_inserts_carousel(seeded_db: str) -> None:
    _run_migration("upgrade", _ORIGIN_REV)

    origins = _origins_by_slug(seeded_db)
    # Pre-existing project-linked row is re-labelled (step 2), not duplicated.
    assert origins[_EXISTING_SLUG] == "carousel"
    # The eligible carousel project produced one backfill-inserted row (step 3).
    inserted_slug = f"carousel-{_CAROUSEL_PROJECT_ID}"
    assert origins[inserted_slug] == "carousel"


# Scenario: downgrade removes ONLY inserted rows and preserves pre-existing data.
def test_downgrade_preserves_preexisting_rows(seeded_db: str) -> None:
    _run_migration("upgrade", _ORIGIN_REV)

    _run_migration("downgrade", _PRE_REV)

    slugs = _slugs(seeded_db)
    # The pre-existing handwritten post SURVIVES the downgrade (no data loss).
    assert _EXISTING_SLUG in slugs
    # The backfill-inserted carousel-* row is removed.
    assert f"carousel-{_CAROUSEL_PROJECT_ID}" not in slugs
    # The origin column is dropped (schema restored).
    conn = sqlite3.connect(seeded_db)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(blog_posts)")}
        assert "origin" not in cols
    finally:
        conn.close()


# Scenario: re-running upgrade is idempotent (no duplicate carousel-derived rows).
def test_upgrade_is_idempotent(seeded_db: str) -> None:
    _run_migration("upgrade", _ORIGIN_REV)
    _run_migration("downgrade", _PRE_REV)
    _run_migration("upgrade", _ORIGIN_REV)

    conn = sqlite3.connect(seeded_db)
    try:
        inserted_slug = f"carousel-{_CAROUSEL_PROJECT_ID}"
        count = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE slug = ?", (inserted_slug,)
        ).fetchone()[0]
        assert count == 1  # exactly one, not duplicated across upgrade cycles
    finally:
        conn.close()
