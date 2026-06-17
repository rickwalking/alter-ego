"""Unit tests for the canonical distribution home accessor (AE-0204).

Prove the ``blog_posts.distribution`` accessor reads + writes the
``{caption, linkedin_post_pt, linkedin_post_en}`` payload SOLELY on the
``origin='carousel'`` row, mirroring the embedded carousel copy.

Gherkin not applicable — this is a focused accessor unit test; the behavioral
contract (byte-identical caption/LinkedIn served from the home) is asserted by the
AE-0125 publishing safety net.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.distribution_home import (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
    build_distribution,
    read_distribution,
    write_distribution,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

_CAPTION = "Home caption"
_LINKEDIN_PT = "Home LinkedIn PT"
_LINKEDIN_EN = "Home LinkedIn EN"


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _project(project_id: str) -> CarouselProject:
    from uuid import UUID

    return CarouselProject(
        id=UUID(project_id),
        topic="t",
        audience="a",
        niche="n",
        caption=_CAPTION,
        linkedin_post_pt=_LINKEDIN_PT,
        linkedin_post_en=_LINKEDIN_EN,
    )


async def _seed_carousel_row(session: AsyncSession, project_id: str) -> None:
    session.add(
        BlogPostModel.from_entity({
            "id": str(uuid4()),
            "project_id": project_id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "t",
            "slug": f"carousel-{project_id}",
            "status": "published",
            "content": {"markdown": "# body"},
        })
    )
    await session.commit()


def test_build_distribution_projects_canonical_shape() -> None:
    # Scenario: build_distribution mirrors the carousel entity into the home shape.
    payload = build_distribution(_project(str(uuid4())))
    assert payload == {
        DISTRIBUTION_CAPTION_KEY: _CAPTION,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: _LINKEDIN_PT,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: _LINKEDIN_EN,
    }


@pytest.mark.asyncio
async def test_write_then_read_round_trips(db_session: AsyncSession) -> None:
    # Scenario: write mirrors into the home; read returns the same payload.
    project_id = str(uuid4())
    await _seed_carousel_row(db_session, project_id)

    await write_distribution(db_session, _project(project_id))
    await db_session.commit()

    result = await read_distribution(db_session, project_id)
    assert result == {
        DISTRIBUTION_CAPTION_KEY: _CAPTION,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: _LINKEDIN_PT,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: _LINKEDIN_EN,
    }


@pytest.mark.asyncio
async def test_read_returns_none_without_carousel_row(
    db_session: AsyncSession,
) -> None:
    # Scenario: no carousel-origin row -> None (callers keep their legacy default).
    assert await read_distribution(db_session, str(uuid4())) is None


@pytest.mark.asyncio
async def test_write_is_noop_without_carousel_row(db_session: AsyncSession) -> None:
    # Scenario: write is a no-op when there is no canonical home to populate.
    project_id = str(uuid4())
    await write_distribution(db_session, _project(project_id))
    await db_session.commit()
    assert await read_distribution(db_session, project_id) is None


@pytest.mark.asyncio
async def test_read_coerces_non_string_to_none(db_session: AsyncSession) -> None:
    # Scenario: a malformed/absent home value reads back as None (no Any leak).
    project_id = str(uuid4())
    await _seed_carousel_row(db_session, project_id)
    result = await read_distribution(db_session, project_id)
    assert result == {
        DISTRIBUTION_CAPTION_KEY: None,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: None,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: None,
    }
