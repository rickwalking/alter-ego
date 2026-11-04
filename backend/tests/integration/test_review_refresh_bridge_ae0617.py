"""Which reworking runs only owe the final-review refresh, on SQLite.

Feature: backend/tests/features/review_refresh_priority_ae0617.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.bootstrap import AutopilotTickConfig
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REVIEW_HOLD_PHASE,
    COVER_REWORK_PHASE,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.autopilot.webhook_constants import AUTOFIX_REWORK_PHASE

pytestmark = pytest.mark.integration

Sessions = async_sessionmaker[AsyncSession]
_REWORKING = AutopilotRunState.REWORKING
_LIMIT = 10


@dataclass(frozen=True, kw_only=True)
class _Carousel:
    """The carousel row a run points at; the default waits in final review."""

    phase: str = PHASE_FINAL_REVIEW
    phase_status: str = PHASE_STATUS_AWAITING_HUMAN
    status: str = CarouselStatus.COMPLETED.value
    workflow_status: str = "draft"
    is_public: bool = False


@pytest_asyncio.fixture(loop_scope="function")
async def sessions() -> AsyncIterator[Sessions]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _bridge(sessions: Sessions) -> AutopilotQueueBridge:
    def no_engine() -> object:
        raise AssertionError("the engine must not be built")

    return AutopilotQueueBridge(
        config=AutopilotTickConfig(
            owner_user_id="owner",
            engine_factory=no_engine,
            stale_after_seconds=180,
        ),
        sessions=sessions,
        retryable=lambda _exc: False,
    )


async def _seed_carousel(sessions: Sessions, carousel: _Carousel) -> str:
    project_id = uuid4().hex
    async with sessions() as session:
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="T",
                audience="builders",
                niche="ai",
                current_phase=carousel.phase,
                phase_status=carousel.phase_status,
                status=carousel.status,
                workflow_status=carousel.workflow_status,
                is_public=carousel.is_public,
            )
        )
        await session.commit()
    return project_id


async def _seed_run(
    sessions: Sessions,
    project_id: str | None,
    state: AutopilotRunState = _REWORKING,
    rework_phase: str | None = None,
) -> UUID:
    topic_id, run_id = uuid4(), uuid4()
    async with sessions() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title="T",
                angle="a",
                why_viral="w",
                audience="builders",
                niche="ai",
                brief="b",
                sources=["https://example.com/a"],
                score=10,
                signal_hash=uuid4().hex,
                status="accepted",
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                carousel_project_id=project_id,
                state=state.value,
                publish_attempts=0,
                telegram_message_ids=[],
                rework_phase=rework_phase,
            )
        )
        await session.commit()
    return run_id


async def test_a_reworking_run_at_final_review_is_a_refresh(
    sessions: Sessions,
) -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    project_id = await _seed_carousel(sessions, _Carousel())
    run_id = await _seed_run(sessions, project_id)
    assert await _bridge(sessions).review_refresh_run_ids(_LIMIT) == [
        (str(run_id), project_id)
    ]


@pytest.mark.parametrize(
    "rework_phase",
    ["content", AUTOFIX_REWORK_PHASE, COVER_REWORK_PHASE, COVER_REVIEW_HOLD_PHASE],
)
async def test_a_queued_rework_is_no_refresh(
    sessions: Sessions, rework_phase: str
) -> None:
    """Scenario Outline: A rework with work left keeps FIFO"""
    project_id = await _seed_carousel(sessions, _Carousel())
    await _seed_run(sessions, project_id, rework_phase=rework_phase)
    assert await _bridge(sessions).review_refresh_run_ids(_LIMIT) == []


@pytest.mark.parametrize(
    "carousel",
    [
        _Carousel(phase="content", phase_status="in_progress"),
        _Carousel(workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH),
        _Carousel(is_public=True),
    ],
    ids=["revise_under_way", "approved_on_website", "released"],
)
async def test_a_carousel_outside_the_review_is_no_refresh(
    sessions: Sessions, carousel: _Carousel
) -> None:
    """Scenario Outline: A rework with work left keeps FIFO"""
    project_id = await _seed_carousel(sessions, carousel)
    await _seed_run(sessions, project_id)
    assert await _bridge(sessions).review_refresh_run_ids(_LIMIT) == []


async def test_a_run_with_no_carousel_is_no_refresh(sessions: Sessions) -> None:
    """Scenario Outline: A rework with work left keeps FIFO"""
    await _seed_run(sessions, None)
    assert await _bridge(sessions).review_refresh_run_ids(_LIMIT) == []


@pytest.mark.parametrize(
    "state",
    [
        AutopilotRunState.QUEUED,
        AutopilotRunState.GENERATING,
        AutopilotRunState.AWAITING_OWNER,
    ],
)
async def test_a_run_in_another_state_is_no_refresh(
    sessions: Sessions, state: AutopilotRunState
) -> None:
    """Scenario: A run in another state is no refresh"""
    project_id = await _seed_carousel(sessions, _Carousel())
    await _seed_run(sessions, project_id, state)
    assert await _bridge(sessions).review_refresh_run_ids(_LIMIT) == []


async def test_the_limit_bounds_the_scan(sessions: Sessions) -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    for _ in range(2):
        await _seed_run(sessions, await _seed_carousel(sessions, _Carousel()))
    assert len(await _bridge(sessions).review_refresh_run_ids(1)) == 1
