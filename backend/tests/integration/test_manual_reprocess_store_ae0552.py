"""SQL-backed manual recovery for each required stuck kind."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.modules.generation_queue.constants import (
    PAYLOAD_MANUAL_ACCELERATE_JOB_ID,
    PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID,
    PAYLOAD_MANUAL_CANCEL_JOB_ID,
    PAYLOAD_MANUAL_ORIGIN,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryOutcome,
    StuckKind,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationStatus,
    WorkflowResumePayload,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from rag_backend.modules.generation_queue.public import build_manual_recovery
from tests.integration.manual_reprocess_support import (
    NOW,
    OLD,
    RecordingNotifier,
    project_row,
    reprocess_audits,
    workflow_run_row,
)
from tests.integration.queue_flow_db_support import queue_flow_engine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _relay_disabled(no_outbox_relay: object) -> None:
    del no_outbox_relay


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _command(project_id: str, run_id: UUID | None = None) -> ManualReprocessCommand:
    return ManualReprocessCommand(
        project_id=project_id, run_id=run_id, actor_id="owner", expected_version=4
    )


async def test_dead_workflow_uses_shared_requeue_and_audit(
    engine: AsyncEngine,
) -> None:
    """Scenario: A dead letter is reprocessed through the queue."""
    sessions = _sessions(engine)
    project_id = str(uuid4())
    old_attempt = uuid4()
    row = workflow_run_row(
        project_id,
        GenerationStatus.DEAD_LETTER,
        finished_at=NOW,
        pgq_job_id=31,
        id=uuid4(),
        **{ATTEMPT_ID_KEY: old_attempt},
    )
    async with sessions() as session:
        session.add_all([project_row(project_id), row])
        await session.commit()
        service = build_manual_recovery(session, RecordingNotifier())
        result = await service.reprocess(_command(project_id, row.id))
        stored = await session.get(GenerationRunModel, row.id)
        audits = await reprocess_audits(session)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.stuck_kind is StuckKind.DEAD_LETTER
    assert result.lock_version == 5
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value
    assert stored.pgq_job_id is None
    assert stored.next_attempt_at is None
    assert stored.last_phase == "content"
    assert stored.attempts == 1
    assert stored.phase_attempts == {"start": 1}
    assert stored.payload[ATTEMPT_ID_KEY] != str(old_attempt)
    assert stored.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"
    assert len(audits) == 1
    assert audits[0].payload == {
        "actor_id": "owner",
        "project_id": project_id,
        "run_id": str(row.id),
        "stuck_kind": "dead_letter",
        "lock_version": 5,
    }


async def test_retry_wait_retains_domain_budgets_and_records_acceleration(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry wait becomes eligible immediately without budget loss."""
    sessions = _sessions(engine)
    project_id = str(uuid4())
    old_attempt = uuid4()
    row = workflow_run_row(
        project_id,
        GenerationStatus.RETRY_WAIT,
        next_attempt_at=NOW + timedelta(minutes=20),
        pgq_job_id=41,
        **{ATTEMPT_ID_KEY: old_attempt},
    )
    async with sessions() as session:
        session.add_all([project_row(project_id), row])
        await session.commit()
        service = build_manual_recovery(session, RecordingNotifier())
        result = await service.reprocess(_command(project_id, row.id))
        stored = await session.get(GenerationRunModel, row.id)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value
    assert stored.next_attempt_at is None
    assert stored.pgq_job_id == 41
    assert stored.attempts == 2
    assert stored.phase_attempts == {"content": 1, "start": 1}
    assert stored.last_phase == "content"
    assert stored.payload[ATTEMPT_ID_KEY] != str(old_attempt)
    assert stored.payload[PAYLOAD_MANUAL_ACCELERATE_JOB_ID] == 41


async def test_stale_running_fences_old_attempt_and_marks_picked_job(
    engine: AsyncEngine,
) -> None:
    """Scenario: A stale running row is taken over safely."""
    sessions = _sessions(engine)
    project_id = str(uuid4())
    old_attempt = uuid4()
    row = workflow_run_row(
        project_id,
        GenerationStatus.RUNNING,
        started_at=OLD,
        pgq_job_id=42,
        **{ATTEMPT_ID_KEY: old_attempt},
    )
    project = project_row(project_id, run_heartbeat_at=OLD)
    async with sessions() as session:
        session.add_all([project, row])
        await session.commit()
        service = build_manual_recovery(session, RecordingNotifier())
        result = await service.reprocess(_command(project_id, row.id))
        stored = await session.get(GenerationRunModel, row.id)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value
    assert stored.pgq_job_id == 42
    assert stored.payload[PAYLOAD_MANUAL_CANCEL_JOB_ID] == 42
    assert stored.payload[PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID] == str(old_attempt)
    new_attempt = stored.payload[ATTEMPT_ID_KEY]
    assert new_attempt != str(old_attempt)
    legacy = SqlGenerationRunStore(sessions)
    assert not await legacy.mark_succeeded(row.id, old_attempt)
    claim = await legacy.mark_running(row.id)
    assert claim is not None
    assert not await legacy.mark_succeeded(row.id, old_attempt)
    assert await legacy.mark_succeeded(row.id, claim)


async def test_orphan_stages_existing_adopt_path(engine: AsyncEngine) -> None:
    """Scenario: A generating project with no active run is adopted."""
    sessions = _sessions(engine)
    project_id = str(uuid4())
    async with sessions() as session:
        session.add(project_row(project_id))
        await session.commit()
        service = build_manual_recovery(session, RecordingNotifier())
        result = await service.reprocess(_command(project_id))
        stored = await session.scalar(
            select(GenerationRunModel).where(
                GenerationRunModel.carousel_project_id == project_id
            )
        )
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.stuck_kind is StuckKind.ORPHAN
    assert stored is not None
    assert stored.id == result.run.id
    assert stored.dedupe_key == f"adopt:{project_id}"
    payload = WorkflowResumePayload.parse(stored.payload)
    assert payload.action == "adopt"
    assert payload.reviewer_id == "generation-queue"
    assert stored.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"
    assert stored.pgq_job_id is None


async def test_running_manual_run_returns_existing_but_fresh_running_is_refused(
    engine: AsyncEngine,
) -> None:
    """Scenario: Double click returns the existing manual run"""
    project_id = str(uuid4())
    run_id = uuid4()
    row = workflow_run_row(
        project_id,
        GenerationStatus.RUNNING,
        id=run_id,
        payload={PAYLOAD_MANUAL_ORIGIN: "carousel_reprocess"},
    )
    async with _sessions(engine)() as session:
        session.add_all([project_row(project_id, run_heartbeat_at=OLD), row])
        await session.commit()
        service = build_manual_recovery(session, RecordingNotifier())
        existing = await service.reprocess(_command(project_id, run_id))
        fresh_project = str(uuid4())
        fresh_run = workflow_run_row(
            fresh_project,
            GenerationStatus.RUNNING,
            payload={PAYLOAD_MANUAL_ORIGIN: "carousel_reprocess"},
        )
        session.add_all([
            project_row(fresh_project, run_heartbeat_at=datetime.now(UTC)),
            fresh_run,
        ])
        await session.commit()
        fresh = await build_manual_recovery(session, RecordingNotifier()).reprocess(
            _command(fresh_project, fresh_run.id)
        )
    assert existing.outcome is RecoveryOutcome.EXISTING
    assert existing.run.id == run_id
    assert fresh.outcome is RecoveryOutcome.REFUSED
    assert fresh.refusal.value == "fresh_running"
