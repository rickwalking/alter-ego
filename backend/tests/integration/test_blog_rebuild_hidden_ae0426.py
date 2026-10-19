"""Hidden-post rebuild end to end (AE-0426, ADR-0025).

Feature: backend/tests/features/blog_rebuild_hidden_ae0426.feature

The real SQL store, the real carousel material source and the real AE-0425
generation service run against a file SQLite DB; only the LLM writer, the voice
scorer and the image provider are fakes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from rag_backend.application.services.blog import (
    blog_generation_service,
    blog_image_batch,
    blog_image_service,
)
from rag_backend.application.services.blog.blog_generation_service import (
    BlogGenerationDeps,
    BlogGenerationService,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    QualityGateDeps,
)
from rag_backend.application.services.blog.blog_rebuild import (
    BlogRebuildService,
    RebuildDeps,
    RebuildSelection,
)
from rag_backend.bootstrap.blog_generation import resolve_persona
from rag_backend.bootstrap.blog_generation_store import (
    RunOwner,
    SlotWriteGenerationStore,
)
from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import (
    CRITERION_CURRENTLY_PUBLISHED,
    CRITERION_MISSING_CAROUSEL,
    CRITERION_MISSING_NOTES,
    HIDDEN_BAD_POST_KEY,
    REBUILT_AT_KEY,
)
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.blog_rebuild_materials import (
    MaterialDeps,
    SqlCarouselMaterialSource,
)
from rag_backend.infrastructure.database.blog_rebuild_store import SqlBlogRebuildStore
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from tests.blog_generation_fakes import (
    FakeImageGenerator,
    FakeScorer,
    FakeWriter,
    article,
    image_batch,
)
from tests.blog_v2_support import v2_content
from tests.integration.conftest import create_test_user

STATE: Mapping[str, object] = {
    "research_findings": [{"summary": "Agentes trabalham.", "key_points": ["rápido"]}],
    "outline": [{"title": "Abertura", "key_points": ["gancho"]}],
}
MISSING_PROJECT = "99999999-9999-9999-9999-999999999999"


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import nullcontext

    for module in (blog_generation_service, blog_image_batch):
        monkeypatch.setattr(module, "blog_phase_trace", lambda _scope: nullcontext())
    monkeypatch.setattr(
        blog_image_service, "blog_ai_propagate", lambda *_args: nullcontext()
    )


@dataclass
class _World:
    """The seeded DB + the wired rebuild service."""

    service: BlogRebuildService


def _build_generation(images_dir: Path, user_id: str) -> BlogGenerationService:
    from rag_backend.infrastructure.database.config import get_session_maker

    return BlogGenerationService(
        BlogGenerationDeps(
            writer=FakeWriter(draft_article=article(3)),
            gate=BlogQualityGate(QualityGateDeps(FakeWriter(), FakeScorer([80.0]))),
            images=image_batch(images_dir, FakeImageGenerator()),
            store=SlotWriteGenerationStore(
                get_session_maker(), RunOwner(user_id=user_id, image_cap=30)
            ),
            timings=GenerationTimings(timeout_seconds=10, heartbeat_seconds=5),
        )
    )


async def _seed_project(slides: int = 3, notes: bool = True) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        project = CarouselProjectModel(
            topic="Agentes de IA",
            audience="devs",
            niche="IA",
            is_public=True,
            content_mode="pov",
            slide_count=slides,
        )
        session.add(project)
        await session.flush()
        for number in range(1, slides + 1):
            session.add(
                CarouselSlideModel(
                    project_id=str(project.id),
                    slide_number=number,
                    slide_type="content",
                    heading=f"Slide {number}",
                    body="corpo",
                    extras={"long_form_notes": f"Nota {number}"} if notes else {},
                )
            )
        await session.commit()
        return str(project.id)


async def _seed_post(
    *,
    project_id: str | None,
    status: str = BlogPostStatus.DRAFT.value,
    content: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> str:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        post = BlogPostModel.from_entity({
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "Antigo",
            "slug": f"antigo-{uuid4()}",
            "status": status,
            "content": content if content is not None else {"sections": []},
            "ai_generation_metadata": metadata if metadata is not None else {},
        })
        session.add(post)
        await session.commit()
        return str(post.id)


async def _fetch(post_id: str) -> BlogPostModel:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        row = await session.get(BlogPostModel, post_id)
        assert row is not None
        return row


async def _count_posts() -> int:
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        return int(
            await session.scalar(select(func.count()).select_from(BlogPostModel))
        )


@pytest.fixture
async def world(tmp_path: Path) -> AsyncIterator[_World]:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0426.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    await create_test_user("owner@ae0426.test", UserRole.EDITOR)
    images_dir = tmp_path / "blog-images"

    async def state(_project_id: str) -> Mapping[str, object] | None:
        return STATE

    from rag_backend.infrastructure.database.config import get_session_maker

    sessions = get_session_maker()
    service = BlogRebuildService(
        RebuildDeps(
            store=SqlBlogRebuildStore(sessions),
            materials=SqlCarouselMaterialSource(
                MaterialDeps(
                    sessions=sessions,
                    workflow_state=state,
                    resolve_persona=resolve_persona,
                )
            ),
            service_factory=lambda _persona, user_id: _build_generation(
                images_dir, user_id
            ),
            clock=lambda: "2026-10-18T00:00:00+00:00",
            new_lease=lambda: str(uuid4()),
        )
    )
    try:
        yield _World(service)
    finally:
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


# Scenario: Dry-run lists the marker-selected rows
async def test_dry_run_selects_only_marked_rows(world: _World) -> None:
    project_id = await _seed_project()
    target = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    await _seed_post(project_id=project_id, metadata={})
    rebuilt = await _seed_post(
        project_id=project_id,
        metadata={HIDDEN_BAD_POST_KEY: {REBUILT_AT_KEY: "2026-10-18"}},
    )
    report = await world.service.preview()
    assert [entry.post_id for entry in report.selected] == [target]
    assert [entry.post_id for entry in report.skipped] == [rebuilt]
    assert (await _fetch(target)).content == {"sections": []}


# Scenario: Dry-run reports missing carousel and missing notes without generating
async def test_dry_run_reports_missing_material(world: _World) -> None:
    with_notes = await _seed_project()
    no_notes = await _seed_project(notes=False)
    good = await _seed_post(
        project_id=with_notes, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    notes_missing = await _seed_post(
        project_id=no_notes, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    orphan = await _seed_post(
        project_id=MISSING_PROJECT, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    report = await world.service.preview()
    assert [entry.post_id for entry in report.selected] == [good]
    skipped = {entry.post_id: entry.criterion for entry in report.skipped}
    assert skipped[notes_missing] == CRITERION_MISSING_NOTES
    assert skipped[orphan] == CRITERION_MISSING_CAROUSEL
    assert (await _fetch(notes_missing)).content == {"sections": []}


# Scenario: A carousel without long_form_notes is skipped, not paid for
async def test_missing_notes_is_skipped(world: _World) -> None:
    project_id = await _seed_project(notes=False)
    target = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    report = await world.service.run()
    assert report.counts == {"selected": 0, "rebuilt": 0, "skipped": 1, "failed": 0}
    assert report.skipped[0].criterion == CRITERION_MISSING_NOTES
    assert (await _fetch(target)).content == {"sections": []}


# Scenario: A published row is not silently unpublished
async def test_published_row_is_skipped_by_default_and_opted_in(world: _World) -> None:
    project_id = await _seed_project()
    target = await _seed_post(
        project_id=project_id,
        status=BlogPostStatus.PUBLISHED.value,
        metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}},
    )
    report = await world.service.run()
    assert report.skipped[0].criterion == CRITERION_CURRENTLY_PUBLISHED
    assert (await _fetch(target)).status == BlogPostStatus.PUBLISHED.value

    report = await world.service.run(RebuildSelection(allow_published=True))
    assert [entry.post_id for entry in report.rebuilt] == [target]
    assert (await _fetch(target)).status == BlogPostStatus.DRAFT.value


# Scenario: The operator narrows the run with --only/--max-posts
async def test_only_and_max_posts_narrow_the_run(world: _World) -> None:
    project_id = await _seed_project()
    first = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    second = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    report = await world.service.run(RebuildSelection(only=frozenset({second})))
    assert [entry.post_id for entry in report.selected] == [second]
    assert (await _fetch(first)).ai_generation_metadata == {
        HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}
    }
    assert (
        REBUILT_AT_KEY
        in (await _fetch(second)).ai_generation_metadata[HIDDEN_BAD_POST_KEY]
    )


# Scenario: A target row is rebuilt as a draft
# Scenario: The rebuild never publishes
async def test_rebuild_produces_a_v2_draft_with_images(world: _World) -> None:
    project_id = await _seed_project(slides=3)
    target = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    report = await world.service.run()
    assert report.counts == {"selected": 1, "rebuilt": 1, "skipped": 0, "failed": 0}
    row = await _fetch(target)
    assert row.status == BlogPostStatus.DRAFT.value
    assert row.status != BlogPostStatus.PUBLISHED.value
    assert row.title == "Título do artigo"
    assert row.published_at is None
    content = row.content
    assert content["schema"] == BLOG_SCHEMA_V2
    assert content["cover"]["url"]
    assert len(content["sections"]) == 3
    assert all(section["image"]["url"] for section in content["sections"])
    assert content["quality"]["voice_score"] == 80.0
    assert content["translations"]["en"]["quality"]["voice_score"] == 80.0
    marker = row.ai_generation_metadata[HIDDEN_BAD_POST_KEY]
    assert marker["at"] == "2026-10-18"
    assert marker[REBUILT_AT_KEY] == "2026-10-18T00:00:00+00:00"


# Scenario: Re-running the script is a no-op
async def test_second_run_is_a_noop_and_creates_no_duplicate(world: _World) -> None:
    project_id = await _seed_project()
    target = await _seed_post(
        project_id=project_id, metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}}
    )
    await world.service.run()
    before = await _fetch(target)
    total_before = await _count_posts()
    report = await world.service.run()
    assert report.counts == {"selected": 0, "rebuilt": 0, "skipped": 1, "failed": 0}
    assert await _count_posts() == total_before
    after = await _fetch(target)
    assert after.slug == before.slug
    assert after.content == before.content


# Scenario: A row already at schema "blog.v2" with a stored quality score is skipped
async def test_v2_with_quality_is_skipped(world: _World) -> None:
    project_id = await _seed_project()
    content = v2_content()
    content["quality"] = {"voice_score": 77.0}
    scored = await _seed_post(
        project_id=project_id,
        content=content,
        metadata={HIDDEN_BAD_POST_KEY: {"at": "2026-10-18"}},
    )
    report = await world.service.run()
    assert report.counts == {"selected": 0, "rebuilt": 0, "skipped": 1, "failed": 0}
    assert (await _fetch(scored)).content["quality"]["voice_score"] == 77.0


# Scenario: A missing carousel is reported and skipped
async def test_missing_carousel_is_skipped_without_error(world: _World) -> None:
    orphan = await _seed_post(
        project_id=MISSING_PROJECT, metadata={HIDDEN_BAD_POST_KEY: {"at": "x"}}
    )
    report = await world.service.run()
    assert [entry.post_id for entry in report.skipped] == [orphan]
    assert report.failed == []
    assert (await _fetch(orphan)).status == BlogPostStatus.DRAFT.value
