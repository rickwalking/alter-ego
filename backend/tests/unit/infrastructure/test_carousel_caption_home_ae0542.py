"""A saved caption survives an empty distribution home; carousel drafts seed it.

Feature: backend/tests/features/approve_keeps_caption_ae0542.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.blog_generation_state import GenerationStart
from rag_backend.infrastructure.database.blog_generation_drafts import (
    GenerationDraftSpec,
    create_generation_draft,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.distribution_home import read_distribution
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

_CAPTION = "Legenda salva pelo Pedro"
_LINKEDIN_PT = "Post do LinkedIn"
_START = GenerationStart(
    kind="k", lease_id="lease", now="2026-10-24T03:00:00Z", request={}
)


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _carousel(db: AsyncSession) -> str:
    project = CarouselProject(
        id=uuid4(),
        topic="t",
        audience="a",
        niche="n",
        caption=_CAPTION,
        linkedin_post_pt=_LINKEDIN_PT,
    )
    await PostgresCarouselRepository(session=db).create_project(project)
    return str(project.id)


def _spec(project_id: str | None, origin: str) -> GenerationDraftSpec:
    return GenerationDraftSpec(
        title="t",
        slug=f"slug-{uuid4()}",
        origin=origin,
        author_id=str(uuid4()),
        start=_START,
        project_id=project_id,
    )


async def _empty_home(
    db: AsyncSession, project_id: str, payload: dict[str, object]
) -> None:
    db.add(
        BlogPostModel.from_entity({
            "id": str(uuid4()),
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "t",
            "slug": f"carousel-{project_id}",
            "status": "draft",
            "content": {},
            "distribution": payload,
        })
    )
    await db.commit()


async def _saved_caption(db: AsyncSession, project_id: str) -> str | None:
    result = await db.execute(
        select(CarouselProjectModel.caption)
        .where(CarouselProjectModel.id == project_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def test_an_empty_home_keeps_the_saved_caption_through_a_save(
    db: AsyncSession,
) -> None:
    """Scenario: A blog draft with an empty distribution never wipes the caption"""
    project_id = await _carousel(db)
    await _empty_home(db, project_id, {})
    repo = PostgresCarouselRepository(session=db)

    loaded = await repo.get_project_by_id(UUID(project_id))
    assert loaded is not None
    assert loaded.caption == _CAPTION
    assert loaded.linkedin_post_pt == _LINKEDIN_PT
    loaded.is_public = True
    await repo.update_project(loaded)

    assert await _saved_caption(db, project_id) == _CAPTION
    home = await read_distribution(db, project_id)
    assert home is not None
    assert home["caption"] == _CAPTION
    assert home["linkedin_post_pt"] == _LINKEDIN_PT


async def test_a_caption_cleared_on_purpose_stays_cleared(db: AsyncSession) -> None:
    """Scenario: A blog draft with an empty distribution never wipes the caption"""
    project_id = await _carousel(db)
    await _empty_home(db, project_id, {"caption": "", "linkedin_post_pt": "novo"})
    loaded = await PostgresCarouselRepository(session=db).get_project_by_id(
        UUID(project_id)
    )
    assert loaded is not None
    assert loaded.caption == ""
    assert loaded.linkedin_post_pt == "novo"


async def test_a_carousel_blog_draft_starts_with_the_saved_copy(
    db: AsyncSession,
) -> None:
    """Scenario: A blog draft from a carousel starts with the carousel's saved copy"""
    project_id = await _carousel(db)
    await create_generation_draft(db, _spec(project_id, BlogPostOrigin.CAROUSEL.value))
    await db.commit()
    home = await read_distribution(db, project_id)
    assert home == {
        "caption": _CAPTION,
        "linkedin_post_pt": _LINKEDIN_PT,
        "linkedin_post_en": None,
    }


@pytest.mark.parametrize("origin", [BlogPostOrigin.STANDALONE.value, None])
async def test_other_drafts_start_with_an_empty_distribution(
    db: AsyncSession, origin: str | None
) -> None:
    """Scenario: A blog draft from a carousel starts with the carousel's saved copy"""
    project_id = await _carousel(db)
    spec = (
        _spec(project_id, origin)
        if origin is not None
        else _spec(str(uuid4()), BlogPostOrigin.CAROUSEL.value)
    )
    lease = await create_generation_draft(db, spec)
    await db.commit()
    row = await db.get(BlogPostModel, lease.post_id)
    assert row is not None
    assert row.distribution == {}
