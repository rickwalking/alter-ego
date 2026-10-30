"""Channel-pluggable publishing counts for the editorial analytics.

Feature: analytics_publishing_channels_ae0500.feature
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.application.services.editorial_analytics_service import (
    EditorialAnalyticsService,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.constants import STATUS_CANDIDATE_ACCEPTED
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ManualPublishModel,
    TopicCandidateModel,
)
from rag_backend.modules.publishing import AnalyticsProjection, AnalyticsQuery
from rag_backend.modules.publishing.infrastructure.publishing_read_acl import (
    PublishingReadAcl,
)

RUN_MEDIA = "17900000000000001"
MANUAL_MEDIA = "17900000000000002"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite in-memory session with the ORM schema created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _post(slug: str) -> BlogPostModel:
    return BlogPostModel.from_entity({
        "title": slug,
        "slug": slug,
        "status": "published",
        "content": {},
        "published_at": datetime.now(UTC),
    })


def _carousel(owner_id: str | None = None) -> CarouselProjectModel:
    return CarouselProjectModel(topic="t", audience="a", niche="n", owner_id=owner_id)


async def _seed_carousel(session: AsyncSession, owner_id: str | None) -> str:
    project = _carousel(owner_id)
    session.add(project)
    await session.flush()
    return project.id


async def _run_publish(
    session: AsyncSession,
    project_id: str,
    media_id: str,
    published_at: datetime,
) -> None:
    topic_id = uuid4()
    session.add(
        TopicCandidateModel(
            id=topic_id,
            title="Agents",
            angle="a",
            why_viral="w",
            audience="devs",
            niche="ai",
            brief="b",
            sources=["https://x.com/a/status/1"],
            score=80,
            signal_hash=uuid4().hex,
            status=STATUS_CANDIDATE_ACCEPTED,
        )
    )
    await session.flush()
    session.add(
        AutopilotRunModel(
            id=uuid4(),
            topic_candidate_id=topic_id,
            carousel_project_id=project_id,
            state=AutopilotRunState.PUBLISHED.value,
            state_reason=None,
            publish_attempts=1,
            telegram_message_ids=[],
            ig_post_id=media_id,
            ig_permalink=f"https://instagram.com/p/{media_id}",
            created_at=published_at,
            updated_at=published_at,
        )
    )


async def _manual_publish(
    session: AsyncSession,
    project_id: str,
    media_id: str,
    claimed_at: datetime,
) -> None:
    session.add(
        ManualPublishModel(
            carousel_project_id=project_id,
            state="published",
            ig_post_id=media_id,
            ig_permalink=f"https://instagram.com/p/{media_id}",
            claimed_at=claimed_at,
        )
    )


def _channels(projection: AnalyticsProjection) -> dict[str, int]:
    return {c.channel: c.published_total for c in projection.summary.channels}


@pytest.mark.asyncio
async def test_published_carousels_count_across_channels(
    db_session: AsyncSession,
) -> None:
    """Scenario: Published carousels count in Publicados and the velocity chart."""
    now = datetime.now(UTC)
    first_id = await _seed_carousel(db_session, None)
    second_id = await _seed_carousel(db_session, None)
    db_session.add_all([_post("one"), _post("two")])
    await _run_publish(db_session, first_id, RUN_MEDIA, now - timedelta(days=1))
    await _manual_publish(db_session, second_id, MANUAL_MEDIA, now - timedelta(days=2))
    await db_session.commit()

    projection = await PublishingReadAcl(db_session).project_analytics(AnalyticsQuery())

    assert projection.summary.published_this_week == 4
    assert projection.summary.published_this_month == 4
    assert _channels(projection) == {"blog": 2, "carousel": 2}
    last_week = projection.velocity_by_week[-1]
    assert last_week.published_count == 4
    assert last_week.channels == {"blog": 2, "carousel": 2}


@pytest.mark.asyncio
async def test_autopilot_and_manual_records_count_one_carousel(
    db_session: AsyncSession,
) -> None:
    """Scenario: A carousel published by autopilot and by manual publish counts once."""
    now = datetime.now(UTC)
    project_id = await _seed_carousel(db_session, None)
    await _run_publish(db_session, project_id, RUN_MEDIA, now - timedelta(days=1))
    await _manual_publish(db_session, project_id, MANUAL_MEDIA, now - timedelta(days=2))
    await db_session.commit()

    projection = await PublishingReadAcl(db_session).project_analytics(AnalyticsQuery())

    assert _channels(projection) == {"blog": 0, "carousel": 1}
    assert projection.summary.published_this_week == 1


@pytest.mark.asyncio
async def test_completed_carousel_without_publish_does_not_count(
    db_session: AsyncSession,
) -> None:
    """Scenario: Carousels without an Instagram publish record do not count."""
    await _seed_carousel(db_session, None)
    await db_session.commit()

    projection = await PublishingReadAcl(db_session).project_analytics(AnalyticsQuery())

    assert _channels(projection)["carousel"] == 0


@pytest.mark.asyncio
async def test_editor_sees_only_own_carousels(db_session: AsyncSession) -> None:
    """Scenario: An editor sees only their own carousels."""
    now = datetime.now(UTC)
    mine = await _seed_carousel(db_session, "owner-a")
    mine_manual = await _seed_carousel(db_session, "owner-a")
    theirs = await _seed_carousel(db_session, "owner-b")
    theirs_manual = await _seed_carousel(db_session, "owner-b")
    await _run_publish(db_session, mine, RUN_MEDIA, now - timedelta(days=1))
    await _manual_publish(
        db_session, mine_manual, MANUAL_MEDIA, now - timedelta(days=1)
    )
    await _run_publish(db_session, theirs, "17900000000000003", now - timedelta(days=1))
    await _manual_publish(
        db_session, theirs_manual, "17900000000000004", now - timedelta(days=1)
    )
    await db_session.commit()

    projection = await PublishingReadAcl(db_session).project_analytics(
        AnalyticsQuery(author_id="owner-a")
    )

    assert _channels(projection) == {"blog": 0, "carousel": 2}
    counts = {c.channel: c for c in projection.summary.channels}
    assert counts["carousel"].published_total == 2


@pytest.mark.asyncio
async def test_average_views_is_removed(db_session: AsyncSession) -> None:
    """Scenario: The average_views dead field is removed."""
    db_session.add(_post("one"))
    await db_session.commit()

    projection = await PublishingReadAcl(db_session).project_analytics(AnalyticsQuery())
    summary = await EditorialAnalyticsService.get_summary(db_session)

    assert not hasattr(projection.summary, "average_views")
    assert "average_views" not in summary
