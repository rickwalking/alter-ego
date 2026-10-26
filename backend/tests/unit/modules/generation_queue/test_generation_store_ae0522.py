"""The SQL store of ``generation_runs`` and the outbox staging, on SQLite."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.infrastructure.database.config import Base
from rag_backend.modules.generation_queue.domain.budget import AttemptCounts
from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
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


def _retry_command(run_id: UUID, attempt_id: UUID, code: str) -> RetryCommand:
    return RetryCommand(
        run_id=run_id,
        attempt_id=attempt_id,
        next_attempt_at=NOW,
        error_code=code,
        error=code,
    )


async def _attempt_writes(
    store: SqlGenerationRunStore, run_id: UUID, attempt_id: UUID
) -> tuple[bool, bool, bool, bool]:
    """Try every attempt-fenced write with the supplied claim."""
    counts = AttemptCounts(attempts=9, phase_attempts={"stale": 9})
    update = CountsUpdate(counts=counts, phase="stale")
    waiting = _retry_command(run_id, attempt_id, "stale")
    dead = AttemptDeadLetterCommand(
        run_id=run_id, attempt_id=attempt_id, error_code="stale", error="stale"
    )
    return (
        await store.save_counts(run_id, attempt_id, update),
        await store.mark_succeeded(run_id, attempt_id),
        await store.mark_waiting(waiting),
        await store.mark_attempt_dead_letter(dead),
    )


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
    attempt_id = await store.mark_running(run.id)
    assert attempt_id is not None
    assert await store.mark_succeeded(run.id, attempt_id)
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
    attempt_id = await store.mark_running(run.id)
    assert attempt_id is not None
    counts = AttemptCounts(attempts=1, phase_attempts={"start": 1})
    update = CountsUpdate(counts=counts, phase="start")
    assert await store.save_counts(run.id, attempt_id, update)
    assert await store.mark_waiting(
        RetryCommand(
            run_id=run.id,
            attempt_id=attempt_id,
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


async def test_wrong_attempt_writes_are_all_rejected(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A stale running row is taken over safely"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    current = await store.mark_running(run.id)
    assert current is not None
    assert await _attempt_writes(store, run.id, uuid4()) == (False,) * 4
    stored = await store.get(run.id)
    assert stored.status is GenerationStatus.RUNNING
    assert stored.attempt_id == current
    assert stored.counts == AttemptCounts(attempts=0, phase_attempts={})


async def test_aba_attempt_writes_are_all_rejected(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A stale running row is taken over safely"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    first = await store.mark_running(run.id)
    assert first is not None
    waiting = _retry_command(run.id, first, "transient")
    assert await store.mark_waiting(waiting)
    second = await store.mark_running(run.id)
    assert second is not None and second != first
    assert await _attempt_writes(store, run.id, first) == (False,) * 4
    stored = await store.get(run.id)
    assert stored.status is GenerationStatus.RUNNING
    assert stored.attempt_id == second
    assert stored.payload["autopilot_run_id"] == "r1"
    assert stored.counts == AttemptCounts(attempts=0, phase_attempts={})


async def test_current_attempt_can_dead_letter(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    attempt_id = await store.mark_running(run.id)
    assert attempt_id is not None
    command = AttemptDeadLetterCommand(
        run_id=run.id, attempt_id=attempt_id, error_code="permanent", error="e"
    )
    assert await store.mark_attempt_dead_letter(command)
    assert not await store.mark_attempt_dead_letter(command)
    assert (await store.get(run.id)).status is GenerationStatus.DEAD_LETTER


async def test_dead_letter_once_and_requeue_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    """Scenario: A dead-lettered run is requeued once"""
    store = SqlGenerationRunStore(sessions)
    await store.stage(autopilot_stage("r1"))
    (run,) = await store.undispatched(1)
    await store.set_job(run.id, 7)
    attempt_id = await store.mark_running(run.id)
    assert attempt_id is not None
    counts = AttemptCounts(attempts=5, phase_attempts={"content": 4, "start": 1})
    update = CountsUpdate(counts=counts, phase="content")
    assert await store.save_counts(run.id, attempt_id, update)
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
    attempt_id = await store.mark_running(run.id)
    assert attempt_id is not None
    assert await store.mark_succeeded(run.id, attempt_id)
    await store.clear_job(run.id)
    finished = await store.get(run.id)
    assert finished.status is GenerationStatus.SUCCEEDED
    assert finished.pgq_job_id == 9
