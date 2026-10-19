"""The AE-0426 script as a real standalone process (prod-container shape).

Feature: backend/tests/features/blog_rebuild_hidden_ae0426.feature

AE-0422's hide script crashed in prod as a standalone process: a circular
import before the app modules loaded, then a ``%``-style structlog call. These
tests run ``python -m rag_backend.scripts.rebuild_hidden_posts`` in a subprocess
to prove ``--help`` needs no settings and a dry run works against the DB.
"""

from __future__ import annotations

import os
import subprocess  # noqa: S404  # integrity-ok: AE-0426 — a standalone-process test must spawn the real module
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import HIDDEN_BAD_POST_KEY
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)

BACKEND = Path(__file__).resolve().parents[3]
MODULE = "rag_backend.scripts.rebuild_hidden_posts"
SECRET_KEY = "test-secret-subprocess-ae0426!!"
ANON_SECRET_KEY = "test-anon-subprocess-ae0426"
MARKER = {HIDDEN_BAD_POST_KEY: {"at": "2026-10-18", "reason": "old"}}


def _env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND / "src")
    env["CAROUSEL_CHECKPOINT_BACKEND"] = "memory"
    env["CAROUSEL_OUTPUT_DIR"] = str(tmp_path / "output")
    env["REDIS_URL"] = ""
    env.pop("LANGFUSE_PUBLIC_KEY", None)
    env.pop("LANGFUSE_SECRET_KEY", None)
    env.pop("LANGFUSE_HOST", None)
    return env


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0426 — fixed interpreter, fixed module, test args
        [sys.executable, "-m", MODULE, *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


async def _seed(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from sqlalchemy.ext.asyncio import async_sessionmaker

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions.begin() as session:
        project = CarouselProjectModel(
            topic="Agentes de IA",
            audience="devs",
            niche="IA",
            is_public=True,
            content_mode="pov",
            slide_count=2,
        )
        session.add(project)
        await session.flush()
        for number in range(1, 3):
            session.add(
                CarouselSlideModel(
                    project_id=str(project.id),
                    slide_number=number,
                    slide_type="content",
                    heading=f"Slide {number}",
                    body="corpo",
                    extras={"long_form_notes": f"Nota {number}"},
                )
            )
        session.add(
            BlogPostModel.from_entity({
                "project_id": str(project.id),
                "origin": BlogPostOrigin.CAROUSEL.value,
                "title": "Antigo",
                "slug": "antigo-subprocess",
                "status": BlogPostStatus.DRAFT.value,
                "content": {"sections": []},
                "ai_generation_metadata": MARKER,
            })
        )
    await engine.dispose()


async def test_help_runs_without_settings(tmp_path: Path) -> None:
    env = _env(tmp_path)
    env.pop("SECRET_KEY", None)
    env.pop("ANON_SECRET_KEY", None)
    env.pop("DATABASE_URL", None)

    result = _run(["--help"], env)

    assert result.returncode == 0, result.stderr
    assert "--apply" in result.stdout
    assert "--dry-run" in result.stdout


async def test_dry_run_against_the_database(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'subprocess.db'}"
    await _seed(database_url)
    env = _env(tmp_path)
    env["DATABASE_URL"] = database_url
    env["SECRET_KEY"] = SECRET_KEY
    env["ANON_SECRET_KEY"] = ANON_SECRET_KEY

    result = _run(["--dry-run"], env)

    assert result.returncode == 0, result.stderr
    assert "selected=1" in result.stdout
    assert "skipped=0" in result.stdout
    assert "failed=0" in result.stdout
