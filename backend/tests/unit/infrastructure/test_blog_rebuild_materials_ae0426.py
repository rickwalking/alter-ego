"""Carousel material source of the AE-0426 rebuild (project-less candidates).

A candidate with no project id (or a malformed one) is ``None`` and returns
before any carousel read.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Mapping

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.application.services.blog.blog_rebuild import RebuildCandidate
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.database.blog_rebuild_materials import (
    MaterialDeps,
    SqlCarouselMaterialSource,
)

PROJECT = "11111111-1111-1111-1111-111111111111"


def _candidate(**overrides: object) -> RebuildCandidate:
    base = RebuildCandidate(
        post_id="post-a",
        project_id=PROJECT,
        author_id=None,
        lock_version=0,
        status="draft",
        has_hidden_marker=True,
        rebuilt_at=None,
        content_schema=None,
        voice_score=None,
    )
    return dataclasses.replace(base, **overrides)


@pytest.fixture
async def source() -> AsyncIterator[SqlCarouselMaterialSource]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _state(_project_id: str) -> Mapping[str, object] | None:
        return None

    async def _persona(
        _session: AsyncSession, _candidates: tuple[str | None, ...]
    ) -> PersonaProfile:
        return PersonaProfile()

    material_source = SqlCarouselMaterialSource(
        MaterialDeps(
            sessions=maker,
            workflow_state=_state,
            resolve_persona=_persona,
        )
    )
    try:
        yield material_source
    finally:
        await engine.dispose()


async def test_candidate_without_project_is_none(
    source: SqlCarouselMaterialSource,
) -> None:
    assert await source.load(_candidate(project_id=None)) is None


async def test_candidate_with_a_malformed_project_is_none(
    source: SqlCarouselMaterialSource,
) -> None:
    assert await source.load(_candidate(project_id="not-a-uuid")) is None
