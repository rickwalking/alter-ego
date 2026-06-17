"""Migration tests for AE-0204 blog_posts.distribution column + backfill.

Gherkin not applicable — this is a schema-migration safety net (DDL/data-movement),
not a behavioral scenario.

These tests run the REAL alembic migration ``e5f6a7b8c9d0`` against a temp SQLite
database and prove the additive distribution home is:

* additive — the column is created NOT NULL with an empty-object default;
* correctly backfilled — every ``origin='carousel'`` row receives
  ``{caption, linkedin_post_pt, linkedin_post_en}`` copied from its linked carousel
  project; standalone rows stay ``{}``;
* reversible round-trip — upgrade head -> downgrade -1 (column dropped) ->
  re-upgrade (column + backfill restored) without touching the embedded source
  columns;
* idempotent — re-running the upgrade re-derives an identical payload.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

_HEAD_BEFORE = "d4e5f6a7b8c9"  # AE-0163 top-up backfill (revision before ours)
_DISTRIBUTION_REV = "e5f6a7b8c9d0"  # AE-0204
_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_CAROUSEL_PROJECT_ID = "project-carousel-dist-1"
_CAROUSEL_BLOG_SLUG = f"carousel-{_CAROUSEL_PROJECT_ID}"
_STANDALONE_BLOG_ID = "standalone-blog-1"
_STANDALONE_SLUG = "my-handwritten-post"

_CAPTION = "Canonical caption"
_LINKEDIN_PT = "Canonical LinkedIn PT"
_LINKEDIN_EN = "Canonical LinkedIn EN"


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


def _seed_pre_distribution_rows(db_path: str) -> None:
    """Seed a carousel project (with distribution copy) + its carousel-origin row.

    Also seeds a standalone blog row to prove only carousel-origin rows are
    backfilled. Run at the ``_HEAD_BEFORE`` revision (origin column exists, the
    distribution column does NOT yet).
    """
    conn = sqlite3.connect(db_path)
    try:
        empty_json = "[]"
        conn.execute(
            """
            INSERT INTO carousel_projects (
                id, is_public, topic, audience, niche, slides_config,
                aspect_ratio, language, generate_images, image_model, image_style,
                theme, status, workflow_status, lock_version, blog_markdown,
                caption, linkedin_post_pt, linkedin_post_en,
                created_at, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, 0, 'gemini', 'comic_neon',
                      'default', 'completed', 'completed', 1, ?, ?, ?, ?,
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
                _CAPTION,
                _LINKEDIN_PT,
                _LINKEDIN_EN,
            ),
        )
        conn.execute(
            """
            INSERT INTO blog_posts (
                id, project_id, origin, title, slug, status, content,
                editor_comments, version_history, sources, citations,
                ai_suggestions, ai_generation_metadata, keywords,
                view_count, like_count, comment_count, share_count, lock_version,
                created_at, updated_at
            ) VALUES (?, ?, 'carousel', ?, ?, 'published', '{}',
                      ?, ?, ?, ?, ?, '{}', ?, 0, 0, 0, 0, 1,
                      datetime('now'), datetime('now'))
            """,
            (
                "carousel-blog-1",
                _CAROUSEL_PROJECT_ID,
                "Carousel post",
                _CAROUSEL_BLOG_SLUG,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
            ),
        )
        conn.execute(
            """
            INSERT INTO blog_posts (
                id, project_id, origin, title, slug, status, content,
                editor_comments, version_history, sources, citations,
                ai_suggestions, ai_generation_metadata, keywords,
                view_count, like_count, comment_count, share_count, lock_version,
                created_at, updated_at
            ) VALUES (?, NULL, 'standalone', ?, ?, 'draft', '{}',
                      ?, ?, ?, ?, ?, '{}', ?, 0, 0, 0, 0, 1,
                      datetime('now'), datetime('now'))
            """,
            (
                _STANDALONE_BLOG_ID,
                "Handwritten post",
                _STANDALONE_SLUG,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
                empty_json,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _distribution_by_slug(db_path: str) -> dict[str, dict[str, object]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT slug, distribution FROM blog_posts").fetchall()
        return {slug: json.loads(dist) for slug, dist in rows}
    finally:
        conn.close()


def _columns(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(blog_posts)")}
    finally:
        conn.close()


@pytest.fixture
def seeded_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A temp DB upgraded to the pre-distribution revision with seeded rows."""
    db_path = str(tmp_path / "distribution_migration.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    _run_migration("upgrade", _HEAD_BEFORE)
    _seed_pre_distribution_rows(db_path)
    return db_path


# Scenario: upgrade adds the column + backfills only carousel-origin rows.
def test_upgrade_backfills_carousel_distribution(seeded_db: str) -> None:
    _run_migration("upgrade", _DISTRIBUTION_REV)

    assert "distribution" in _columns(seeded_db)
    distributions = _distribution_by_slug(seeded_db)
    # The carousel-origin row is backfilled from the embedded carousel columns.
    carousel = distributions[_CAROUSEL_BLOG_SLUG]
    assert carousel == {
        "caption": _CAPTION,
        "linkedin_post_pt": _LINKEDIN_PT,
        "linkedin_post_en": _LINKEDIN_EN,
    }
    # The standalone row is NOT backfilled — it keeps the empty-object default.
    assert distributions[_STANDALONE_SLUG] == {}


# Scenario: downgrade drops the column without touching the embedded source data.
def test_downgrade_drops_column_no_data_loss(seeded_db: str) -> None:
    _run_migration("upgrade", _DISTRIBUTION_REV)

    _run_migration("downgrade", _HEAD_BEFORE)

    assert "distribution" not in _columns(seeded_db)
    # The embedded source columns (the backfill source) are untouched.
    conn = sqlite3.connect(seeded_db)
    try:
        caption = conn.execute(
            "SELECT caption FROM carousel_projects WHERE id = ?",
            (_CAROUSEL_PROJECT_ID,),
        ).fetchone()[0]
        assert caption == _CAPTION
    finally:
        conn.close()


# Scenario: re-running upgrade is idempotent (identical payload, column restored).
def test_upgrade_round_trip_is_idempotent(seeded_db: str) -> None:
    _run_migration("upgrade", _DISTRIBUTION_REV)
    _run_migration("downgrade", _HEAD_BEFORE)
    _run_migration("upgrade", _DISTRIBUTION_REV)

    distributions = _distribution_by_slug(seeded_db)
    assert distributions[_CAROUSEL_BLOG_SLUG] == {
        "caption": _CAPTION,
        "linkedin_post_pt": _LINKEDIN_PT,
        "linkedin_post_en": _LINKEDIN_EN,
    }
