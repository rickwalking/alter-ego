"""The SQL store of ``generation_runs`` and the outbox staging, on SQLite."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.infrastructure.database.config import Base
from rag_backend.modules.generation_queue.domain.budget import AttemptCounts
from rag_backend.modules.generation_queue.domain.models import (
    CountsUpdate,
    DeadLetterCommand,
    GenerationKind,
    GenerationStatus,
    RetryCommand,
    WorkflowResumePayload,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from rag_backend.modules.generation_queue.public import stage_workflow_resume
from tests.unit.modules.generation_queue.queue_fakes import NOW, FixedClock

_PAYLOAD = WorkflowResumePayload(
    project_id="p1", action="approve", reviewer_id="u1", project_title="T"
)


@pytest.fixture
async def sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all, tables=[GenerationRunModel.__table__]
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _stage_resume(
    sessions: async_sessionmaker[AsyncSession], lock_version: int
) -> bool:
    async with sessions() as session:
        inserted = await stage_workflow_resume(session, _PAYLOAD, lock_version)
        await session.commit()
        return inserted


async def test_same_stage_twice_keeps_one_active_run(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: The same confirmation twice queues one run"""
    store = SqlGenerationRunStore(sessions)
    assert await _stage_resume(sessions, 2)
    assert not await _stage_resume(sessions, 2)
    assert await _stage_resume(sessions, 3)
    assert await store.stage(autopilot_stage("r1"))
    assert not await store.stage(autopilot_stage("r1"))
    queued = await store.undispatched(10)
    assert [run.dedupe_key for run in queued] == [
        "resume:p1:2",
        "resume:p1:3",
        "autopilot:r1",
    ]
    assert queued[0].kind is GenerationKind.WORKFLOW_RESUME
    assert WorkflowResumePayload.parse(queued[0].payload) == _PAYLOAD


async def test_stage_rolls_back_with_the_approval(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: The dashboard resume is queued, not run in the web process"""
    async with sessions() as session:
        await stage_workflow_resume(session, _PAYLOAD, 2)
        await session.rollback()
    assert await SqlGenerationRunStore(sessions).undispatched(10) == []


async def test_a_finished_run_frees_its_dedupe_key(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: The same confirmation twice queues one run"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    assert await store.mark_running(run.id)
    await store.mark_succeeded(run.id)
    assert (await store.get(run.id)).status is GenerationStatus.SUCCEEDED
    assert await store.stage(autopilot_stage("r1"))


async def test_the_injected_clock_stamps_the_staged_run(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: Queue health is reported and alerts fire once per episode"""
    store = SqlGenerationRunStore(sessions, FixedClock())
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    assert run.created_at.replace(tzinfo=NOW.tzinfo) == NOW


async def test_lifecycle_and_compare_and_set(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1", "p1"))
    (run,) = await store.undispatched(1)
    await store.set_job(run.id, 42)
    assert await store.undispatched(1) == []
    assert [item.pgq_job_id for item in await store.dispatched_active(5)] == [42]
    assert await store.mark_running(run.id)
    counts = AttemptCounts(attempts=1, phase_attempts={"start": 1})
    await store.save_counts(run.id, CountsUpdate(counts=counts, phase="start"))
    await store.mark_waiting(
        RetryCommand(
            run_id=run.id,
            next_attempt_at=NOW + timedelta(seconds=30),
            error_code="transient",
            error="TimeoutError: x",
        )
    )
    stored = await store.get(run.id)
    assert stored.status is GenerationStatus.RETRY_WAIT
    assert stored.attempts == 1
    assert stored.phase_attempts == {"start": 1}
    assert stored.last_phase == "start"
    assert stored.last_error_code == "transient"
    await store.clear_job(run.id)
    cleared = await store.get(run.id)
    assert cleared.pgq_job_id is None
    assert cleared.status is GenerationStatus.QUEUED


async def test_dead_letter_once_and_requeue_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A dead-lettered run is requeued once"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    await store.set_job(run.id, 7)
    counts = AttemptCounts(attempts=5, phase_attempts={"content": 4, "start": 1})
    await store.save_counts(run.id, CountsUpdate(counts=counts, phase="content"))
    command = DeadLetterCommand(run_id=run.id, error_code="phase", error="e")
    assert await store.mark_dead_letter(command)
    assert not await store.mark_dead_letter(command)
    assert not await store.mark_running(run.id)
    assert await store.requeue_dead_letter(run.id)
    requeued = await store.get(run.id)
    assert requeued.status is GenerationStatus.QUEUED
    assert requeued.pgq_job_id is None
    assert requeued.attempts == 1
    assert requeued.phase_attempts == {"start": 1}
    assert not await store.requeue_dead_letter(run.id)


async def test_other_active_resume_for_a_project(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A queued dashboard resume owns its in-progress project"""
    store = SqlGenerationRunStore(sessions)
    await _stage_resume(sessions, 2)
    await store.stage(autopilot_stage("r1", "p1"))
    resume, drive = await store.undispatched(5)
    assert await store.other_active_for_project("p1", drive.id)
    assert not await store.other_active_for_project("p1", resume.id)
    assert not await store.other_active_for_project("p2", drive.id)


async def test_requeue_is_refused_while_a_newer_run_holds_the_key(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A dead-lettered run is requeued once"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    await store.mark_dead_letter(
        DeadLetterCommand(run_id=run.id, error_code="permanent", error="e")
    )
    assert await store.stage(autopilot_stage("r1"))
    assert not await store.requeue_dead_letter(run.id)
    assert (await store.get(run.id)).status is GenerationStatus.DEAD_LETTER


async def test_a_finished_run_is_never_requeued_as_lost(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A lost job is handed over again"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    await store.set_job(run.id, 9)
    await store.mark_running(run.id)
    await store.mark_succeeded(run.id)
    await store.clear_job(run.id)
    finished = await store.get(run.id)
    assert finished.status is GenerationStatus.SUCCEEDED
    assert finished.pgq_job_id == 9
