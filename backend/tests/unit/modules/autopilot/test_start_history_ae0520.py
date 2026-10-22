"""The latest autopilot start is read from the runs' carousel creation times.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.start_history import (
    SqlStartHistory,
)

_FIRST = datetime(2026, 10, 22, 11, 5, tzinfo=UTC)
_SECOND = datetime(2026, 10, 22, 11, 25, tzinfo=UTC)


async def _run(session: AsyncSession, created_at: datetime | None) -> UUID:
    """A run; with ``created_at`` it is attached to a carousel created then."""
    project_id: str | None = None
    if created_at is not None:
        project_id = str(uuid.uuid4())
        session.add(
            CarouselProjectModel(
                id=project_id, topic="t", audience="a", niche="n", created_at=created_at
            )
        )
        await session.flush()
    repo = SqlAlchemyAutopilotRepository(session)
    topic = TopicCandidate(
        candidate_id=uuid4(),
        title="t",
        angle="a",
        why_viral="w",
        audience="a",
        niche="n",
        brief="b",
        sources=(),
        score=80,
        signal_hash=uuid4().hex,
        status="queued",
    )
    await repo.add_topic(topic)
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=project_id,
        state=AutopilotRunState.GENERATING,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    await repo.add(run)
    await session.commit()
    return run.run_id


@pytest.mark.unit
async def test_latest_start_is_the_newest_carousel_of_another_run(
    db_session: AsyncSession,
) -> None:
    # Scenario: The latest start is the newest carousel created by another run
    await _run(db_session, _FIRST)
    second = await _run(db_session, _SECOND)
    queued = await _run(db_session, None)
    history = SqlStartHistory(db_session)

    assert await history.latest_start(second) == _FIRST
    assert await history.latest_start(queued) == _SECOND


@pytest.mark.unit
async def test_no_latest_start_without_another_attached_run(
    db_session: AsyncSession,
) -> None:
    # Scenario: The latest start is the newest carousel created by another run
    only = await _run(db_session, _FIRST)
    await _run(db_session, None)

    assert await SqlStartHistory(db_session).latest_start(only) is None
