"""Queue order, drive times and the in-transaction dead-letter requeue (SQLite).

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.public import (
    active_queue,
    recent_drive_minutes,
    requeue_autopilot_dead_letter,
)
from tests.integration.queue_flow_db_support import queue_flow_engine

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
_S = AutopilotRunState


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _generation(
    engine: AsyncEngine,
    autopilot_run_id: str | None,
    status: str,
    minutes_ago: int,
) -> UUID:
    run_id = uuid4()
    created = _NOW - timedelta(minutes=minutes_ago)
    async with _sessions(engine)() as session:
        session.add(
            GenerationRunModel(
                id=run_id,
                kind="autopilot_drive",
                dedupe_key=f"autopilot:{autopilot_run_id or run_id}",
                status=status,
                payload={},
                autopilot_run_id=autopilot_run_id,
                attempts=3,
                phase_attempts={"content": 2, "outline": 1},
                last_phase="content",
                created_at=created,
                started_at=created,
                finished_at=created + timedelta(minutes=minutes_ago // 2 or 1),
                updated_at=created,
            )
        )
        await session.commit()
    return run_id


async def _autopilot_run(
    engine: AsyncEngine,
    state: _S,
    minutes_ago: int,
    pov: tuple[str | None, str | None] = (None, None),
) -> str:
    """``pov`` is the topic's content mode and the run's confirmed thesis."""
    mode, thesis = pov
    topic_id, run_id = uuid4(), uuid4()
    created = _NOW - timedelta(minutes=minutes_ago)
    async with _sessions(engine)() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title=f"t {run_id.hex[:5]}",
                angle="a",
                why_viral="w",
                audience="a",
                niche="n",
                brief="b",
                sources=["https://example.com/a"],
                score=1,
                signal_hash=uuid4().hex,
                status="accepted",
                content_mode=mode,
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                state=state.value,
                state_reason=None,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=created,
                updated_at=created,
                pov_thesis=thesis,
            )
        )
        await session.commit()
    return str(run_id)


async def test_the_queue_order_and_drive_times(engine: AsyncEngine) -> None:
    """Scenario: The position counts the runs ahead in FIFO order"""
    await _generation(engine, "running", "running", 30)
    await _generation(engine, None, "queued", 20)
    await _generation(engine, "done", "succeeded", 40)
    await _generation(engine, "parked", "dead_letter", 50)
    async with _sessions(engine)() as session:
        work = await active_queue(session)
        minutes = await recent_drive_minutes(session, 10)
    assert [w.autopilot_run_id for w in work] == ["running", None]
    assert minutes == [20.0]


async def test_the_adapter_snapshot_puts_unstaged_runs_after_the_active_ones(
    engine: AsyncEngine,
) -> None:
    """Scenario: The position counts the runs ahead in FIFO order"""
    staged = await _autopilot_run(engine, _S.GENERATING, 60)
    await _generation(engine, staged, "running", 30)
    older = await _autopilot_run(engine, _S.QUEUED, 20)
    confirmed = await _autopilot_run(engine, _S.QUEUED, 15, ("pov", "Tese"))
    await _autopilot_run(engine, _S.QUEUED, 12, ("pov_news", None))
    newer = await _autopilot_run(engine, _S.QUEUED, 10)
    await _autopilot_run(engine, _S.AWAITING_THESIS, 5)
    async with _sessions(engine)() as session:
        snapshot = await SqlQueueControl(session).snapshot()
    assert snapshot.ahead == (staged,)
    assert snapshot.waiting == (older, confirmed, newer)
    assert snapshot.drive_minutes == ()


async def test_a_dead_letter_is_requeued_once_with_the_failing_phase_reset(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry resumes a run that died mid-generation"""
    run = await _autopilot_run(engine, _S.ESCALATED, 30)
    dead = await _generation(engine, run, "dead_letter", 30)
    async with _sessions(engine)() as session:
        control = SqlQueueControl(session)
        first = await control.requeue_dead_letter(UUID(run))
        second = await requeue_autopilot_dead_letter(session, run)
        await session.commit()
        row = await session.get(GenerationRunModel, dead)
    assert (first, second) == (True, False)
    assert row is not None
    assert row.status == "queued"
    assert row.phase_attempts == {"outline": 1}
    assert row.attempts == 1
    assert row.finished_at is None


async def test_a_requeue_yields_to_an_active_run_with_the_same_key(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry happens once"""
    run = await _autopilot_run(engine, _S.ESCALATED, 30)
    dead = await _generation(engine, run, "dead_letter", 30)
    await _generation(engine, run, "queued", 5)
    async with _sessions(engine)() as session:
        moved = await requeue_autopilot_dead_letter(session, run)
        await session.commit()
        status = await session.scalar(
            select(GenerationRunModel.status).where(GenerationRunModel.id == dead)
        )
    assert moved is False
    assert status == "dead_letter"
