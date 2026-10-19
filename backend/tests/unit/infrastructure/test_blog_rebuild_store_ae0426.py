"""SQL adapter of the AE-0426 rebuild (candidates + the two fenced writes).

Feature: backend/tests/features/blog_rebuild_hidden_ae0426.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.application.services.blog.blog_rebuild import AttemptSpec, RebuiltStamp
from rag_backend.domain.constants.ai_disclosure import AI_DISCLOSURE_GENERATED
from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.blog_rebuild import (
    HIDDEN_BAD_POST_KEY,
    REBUILD_STATUS_KEY,
    REBUILT_AT_KEY,
)
from rag_backend.domain.models.blog_generation_state import GenerationStart
from rag_backend.infrastructure.database.blog_rebuild_store import SqlBlogRebuildStore
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

SessionFactory = async_sessionmaker[AsyncSession]
MARKER = {HIDDEN_BAD_POST_KEY: {"at": "2026-10-18", "reason": "old"}}
_STAMP = datetime(2026, 1, 1, tzinfo=UTC)
START = GenerationStart(
    kind="from_carousel",
    lease_id="lease-1",
    now="2026-10-18T00:00:00+00:00",
    request={},
)


@dataclass
class _Fixture:
    """The store under test plus the session factory that owns the engine."""

    store: SqlBlogRebuildStore
    sessions: SessionFactory


@pytest.fixture
async def fixture(tmp_path: Path) -> AsyncIterator[_Fixture]:
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'store.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield _Fixture(store=SqlBlogRebuildStore(sessions), sessions=sessions)
    finally:
        await engine.dispose()


async def _seed(fixture: _Fixture, **overrides: object) -> str:
    post_id = str(uuid4())
    entity: dict[str, object] = {
        "id": post_id,
        "project_id": str(uuid4()),
        "origin": BlogPostOrigin.CAROUSEL.value,
        "title": "Old",
        "slug": f"old-{post_id}",
        "status": BlogPostStatus.DRAFT.value,
        "content": {"sections": []},
        "ai_generation_metadata": {},
        "published_at": _STAMP,
        "submitted_for_review_at": _STAMP,
    }
    entity.update(overrides)
    async with fixture.sessions.begin() as session:
        session.add(BlogPostModel.from_entity(entity))
    return post_id


async def _row(fixture: _Fixture, post_id: str) -> BlogPostModel:
    async with fixture.sessions() as session:
        row = await session.get(BlogPostModel, post_id)
        assert row is not None
        return row


async def test_candidates_reports_marker_and_document_facts(fixture: _Fixture) -> None:
    marked = await _seed(
        fixture,
        ai_generation_metadata=MARKER,
        content={"schema": "blog.v2", "quality": {"voice_score": 71.5}},
    )
    plain = await _seed(fixture)
    candidates = {
        candidate.post_id: candidate for candidate in await fixture.store.candidates()
    }
    assert set(candidates) == {marked, plain}
    assert candidates[marked].has_hidden_marker is True
    assert candidates[marked].rebuilt_at is None
    assert candidates[marked].content_schema == "blog.v2"
    assert candidates[marked].voice_score == 71.5
    assert candidates[plain].has_hidden_marker is False


async def test_candidates_ignores_a_boolean_voice_score(fixture: _Fixture) -> None:
    post_id = await _seed(
        fixture,
        ai_generation_metadata=MARKER,
        content={"quality": {"voice_score": True}},
    )
    candidate = next(
        c for c in await fixture.store.candidates() if c.post_id == post_id
    )
    assert candidate.voice_score is None


async def test_start_attempt_drafts_the_row_and_cas_fences_it(
    fixture: _Fixture,
) -> None:
    post_id = await _seed(fixture, ai_generation_metadata=MARKER)
    seen = next(
        c for c in await fixture.store.candidates() if c.post_id == post_id
    ).lock_version
    lease = await fixture.store.start_attempt(
        AttemptSpec(post_id=post_id, seen_lock_version=seen, start=START)
    )
    assert lease is not None
    assert lease.lock_version == seen + 1
    row = await _row(fixture, post_id)
    assert row.status == BlogPostStatus.DRAFT.value
    assert row.content["schema"] == BLOG_SCHEMA_V2
    assert row.content["cover"] is None
    assert row.featured_image_url is None
    assert row.published_at is None
    assert row.submitted_for_review_at is None
    assert row.ai_disclosure_label == AI_DISCLOSURE_GENERATED
    assert (
        row.ai_generation_metadata[HIDDEN_BAD_POST_KEY] == MARKER[HIDDEN_BAD_POST_KEY]
    )

    stale = await fixture.store.start_attempt(
        AttemptSpec(post_id=post_id, seen_lock_version=seen, start=START)
    )
    assert stale is None


async def test_start_attempt_refuses_a_published_row_unless_allowed(
    fixture: _Fixture,
) -> None:
    post_id = await _seed(
        fixture,
        status=BlogPostStatus.PUBLISHED.value,
        ai_generation_metadata=MARKER,
    )
    seen = next(
        c for c in await fixture.store.candidates() if c.post_id == post_id
    ).lock_version
    refused = await fixture.store.start_attempt(
        AttemptSpec(post_id=post_id, seen_lock_version=seen, start=START)
    )
    assert refused is None
    assert (await _row(fixture, post_id)).status == BlogPostStatus.PUBLISHED.value

    allowed = await fixture.store.start_attempt(
        AttemptSpec(
            post_id=post_id,
            seen_lock_version=seen,
            start=START,
            allow_published=True,
        )
    )
    assert allowed is not None
    assert (await _row(fixture, post_id)).status == BlogPostStatus.DRAFT.value


async def test_mark_rebuilt_stamps_the_existing_marker(fixture: _Fixture) -> None:
    post_id = await _seed(fixture, ai_generation_metadata=MARKER)
    await fixture.store.mark_rebuilt(
        RebuiltStamp(post_id=post_id, at="2026-10-18T01:00:00+00:00", status="complete")
    )
    marker = (await _row(fixture, post_id)).ai_generation_metadata[HIDDEN_BAD_POST_KEY]
    assert marker["reason"] == "old"
    assert marker[REBUILT_AT_KEY] == "2026-10-18T01:00:00+00:00"
    assert marker[REBUILD_STATUS_KEY] == "complete"
