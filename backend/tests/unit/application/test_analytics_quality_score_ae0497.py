"""The analytics quality score averages real content scores, or is empty.

Feature: analytics_quality_score_ae0497.feature
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from rag_backend.application.services.editorial_analytics_service import (
    EditorialAnalyticsService,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.persona_rubric import (
    QualityRubricModel,
    RubricEvaluationScoreModel,
)
from rag_backend.modules.publishing import AnalyticsQuery
from rag_backend.modules.publishing.infrastructure.publishing_read_acl import (
    PublishingReadAcl,
)

AD_HOC_CONTENT_ID = str(UUID(int=0))


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


def _post(slug: str, status: str) -> BlogPostModel:
    return BlogPostModel.from_entity({
        "title": slug,
        "slug": slug,
        "status": status,
        "content": {},
        "published_at": datetime.now(UTC) if status == "published" else None,
    })


async def _scores(session: AsyncSession, scores: list[tuple[str, int]]) -> None:
    rubric = QualityRubricModel(name="Checks", criteria=[])
    session.add(rubric)
    await session.flush()
    for content_id, overall in scores:
        session.add(
            RubricEvaluationScoreModel(
                rubric_id=rubric.id,
                content_id=content_id,
                content_type="carousel",
                scores={},
                overall_score=overall,
                passed=overall >= 70,
                feedback=[],
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_without_content_scores_the_score_is_empty(
    db_session: AsyncSession,
) -> None:
    # Scenario: Without content scores the quality score is empty
    db_session.add_all([_post("one", "published"), _post("two", "draft")])
    await db_session.commit()

    summary = await EditorialAnalyticsService().get_summary(db_session)

    assert summary["quality_score_average"] is None
    assert summary["quality_score_count"] == 0


@pytest.mark.asyncio
async def test_the_score_averages_the_content_scores(
    db_session: AsyncSession,
) -> None:
    # Scenario: The quality score averages the content scores
    await _scores(db_session, [(str(uuid4()), 80), (str(uuid4()), 61)])

    projection = await PublishingReadAcl(db_session).project_analytics(
        AnalyticsQuery(weeks=1)
    )

    assert projection.summary.quality_score_average == 70.5
    assert projection.summary.quality_score_count == 2


@pytest.mark.asyncio
async def test_ad_hoc_evaluations_are_not_counted(db_session: AsyncSession) -> None:
    # Scenario: Ad-hoc evaluations of pasted text are not counted
    await _scores(db_session, [(AD_HOC_CONTENT_ID, 10), (str(uuid4()), 90)])

    projection = await PublishingReadAcl(db_session).project_analytics(
        AnalyticsQuery(weeks=1)
    )

    assert projection.summary.quality_score_average == 90.0
    assert projection.summary.quality_score_count == 1


@pytest.mark.asyncio
async def test_empty_score_maps_to_none_in_the_projection(
    db_session: AsyncSession,
) -> None:
    # Scenario: Without content scores the quality score is empty
    projection = await PublishingReadAcl(db_session).project_analytics(
        AnalyticsQuery(weeks=1)
    )

    assert projection.summary.quality_score_average is None
    assert projection.summary.quality_score_count == 0
