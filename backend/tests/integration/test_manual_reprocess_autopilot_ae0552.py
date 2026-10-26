"""Autopilot revive, failed-terminal successor and daily-cap integration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.ports import DayWindow
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.generation_queue.constants import (
    PAYLOAD_MANUAL_ORIGIN,
    PAYLOAD_MANUAL_REPLACES_RUN_ID,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryOutcome,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationKind,
    GenerationStatus,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.public import build_manual_recovery
from tests.integration.manual_reprocess_support import (
    NOW,
    RecordingNotifier,
    autopilot_run_row,
    project_row,
    reprocess_audits,
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


def _topic(topic_id: UUID) -> TopicCandidateModel:
    return TopicCandidateModel(
        id=topic_id,
        title="Safe title",
        angle="Angle",
        why_viral="Why",
        audience="Builders",
        niche="AI",
        brief="Brief",
        sources=[],
        score=90,
        signal_hash=uuid4().hex,
        status="promoted",
        created_at=NOW - timedelta(hours=2),
    )


async def _seed_topic(session: AsyncSession, topic_id: UUID) -> None:
    session.add(_topic(topic_id))
    await session.flush()


def _autopilot(
    topic_id: UUID, run_id: UUID, state: AutopilotRunState, **overrides: object
) -> AutopilotRunModel:
    values: dict[str, object] = {
        "id": run_id,
        "topic_candidate_id": topic_id,
        "state": state.value,
        "state_reason": "queue_dead_letter:permanent",
        "publish_attempts": 0,
        "start_attempts": 0,
        "telegram_message_ids": [],
        "created_at": NOW - timedelta(hours=1),
        "updated_at": NOW - timedelta(hours=1),
    }
    values.update(overrides)
    return AutopilotRunModel(**values)


def _command(
    run_id: UUID | None, project_id: str | None = None
) -> ManualReprocessCommand:
    return ManualReprocessCommand(
        project_id=project_id,
        run_id=run_id,
        actor_id="admin",
        expected_version=4 if project_id else None,
    )


async def _cap_count(session: AsyncSession) -> int:
    window = DayWindow(start=NOW - timedelta(days=1), end=NOW + timedelta(days=1))
    return await SqlAlchemyTopicIntakeStore(session).runs_created_between(window)


async def test_failed_terminal_successor_is_durable_idempotent_and_outside_cap(
    engine: AsyncEngine,
) -> None:
    """Scenario: Manual recovery is outside cap and backlog and keeps class FIFO"""
    sessions = _sessions(engine)
    topic_id, autopilot_id, generation_id = uuid4(), uuid4(), uuid4()
    old = autopilot_run_row(
        autopilot_id, GenerationStatus.DEAD_LETTER, id=generation_id
    )
    notifier = RecordingNotifier()
    async with sessions() as session:
        await _seed_topic(session, topic_id)
        session.add_all([
            _autopilot(topic_id, autopilot_id, AutopilotRunState.FAILED),
            old,
        ])
        await session.commit()
        before = await _cap_count(session)
        service = build_manual_recovery(session, notifier)
        accepted = await service.reprocess(_command(generation_id))
        again = await service.reprocess(_command(generation_id))
        after = await _cap_count(session)
        successor = await session.get(GenerationRunModel, accepted.run.id)
        autopilot_rows = list((await session.scalars(select(AutopilotRunModel))).all())
        audits = await reprocess_audits(session)
        active = await session.scalar(
            select(func.count())
            .select_from(GenerationRunModel)
            .where(GenerationRunModel.status.in_(("queued", "running", "retry_wait")))
        )
        candidates = await session.scalar(
            select(func.count()).select_from(TopicCandidateModel)
        )
    assert accepted.outcome is RecoveryOutcome.QUEUED
    assert accepted.run.id != generation_id
    assert again.outcome is RecoveryOutcome.EXISTING
    assert again.run.id == accepted.run.id
    assert successor is not None
    assert successor.payload[PAYLOAD_MANUAL_REPLACES_RUN_ID] == str(generation_id)
    assert successor.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"
    assert successor.payload[ATTEMPT_ID_KEY]
    assert before == after == 1
    assert len(autopilot_rows) == 2
    assert (
        sum(row.state == AutopilotRunState.QUEUED.value for row in autopilot_rows) == 1
    )
    assert active == 1
    assert candidates == 1
    assert len(audits) == 1
    assert len(notifier.notices) == 2
    async with sessions() as session:
        successor = await session.get(GenerationRunModel, accepted.run.id)
        assert successor is not None
        successor.status = GenerationStatus.RUNNING.value
        await session.commit()
        running_again = await build_manual_recovery(
            session, RecordingNotifier()
        ).reprocess(_command(generation_id))
    assert running_again.outcome is RecoveryOutcome.EXISTING
    assert running_again.run.id == accepted.run.id


async def test_escalated_autopilot_uses_existing_revive_and_requeue(
    engine: AsyncEngine,
) -> None:
    """Scenario: A dead autopilot drive revives through the existing CAS path."""
    sessions = _sessions(engine)
    topic_id, autopilot_id, generation_id = uuid4(), uuid4(), uuid4()
    project_id = str(uuid4())
    generation = autopilot_run_row(
        autopilot_id,
        GenerationStatus.DEAD_LETTER,
        id=generation_id,
        carousel_project_id=project_id,
        pgq_job_id=55,
    )
    async with sessions() as session:
        await _seed_topic(session, topic_id)
        session.add_all([
            project_row(project_id),
            _autopilot(
                topic_id,
                autopilot_id,
                AutopilotRunState.ESCALATED,
                carousel_project_id=project_id,
            ),
            generation,
        ])
        await session.commit()
        before = await _cap_count(session)
        service = build_manual_recovery(session, RecordingNotifier())
        result = await service.reprocess(_command(generation_id, project_id))
        after = await _cap_count(session)
        autopilot = await session.get(AutopilotRunModel, autopilot_id)
        stored = await session.get(GenerationRunModel, generation_id)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.run.id == generation_id
    assert autopilot is not None
    assert autopilot.state == AutopilotRunState.GENERATING.value
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value
    assert stored.pgq_job_id is None
    assert stored.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"
    assert stored.payload[ATTEMPT_ID_KEY]
    assert before == after == 1


async def test_retry_wait_reprocess_does_not_free_an_autopilot_cap_slot(
    engine: AsyncEngine,
) -> None:
    """Scenario: Manual recovery is outside cap and backlog and keeps class FIFO"""
    sessions = _sessions(engine)
    topic_id, autopilot_id, generation_id = uuid4(), uuid4(), uuid4()
    generation = autopilot_run_row(
        autopilot_id,
        GenerationStatus.RETRY_WAIT,
        id=generation_id,
        next_attempt_at=NOW + timedelta(hours=1),
    )
    async with sessions() as session:
        await _seed_topic(session, topic_id)
        session.add_all([
            _autopilot(
                topic_id,
                autopilot_id,
                AutopilotRunState.GENERATING,
                state_reason="retry_scheduled",
            ),
            generation,
        ])
        await session.commit()
        before = await _cap_count(session)
        result = await build_manual_recovery(session, RecordingNotifier()).reprocess(
            _command(generation_id)
        )
        after = await _cap_count(session)
        stored = await session.get(GenerationRunModel, generation_id)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.run.id == generation_id
    assert stored is not None
    assert stored.status == GenerationStatus.QUEUED.value
    assert stored.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"
    assert PAYLOAD_MANUAL_REPLACES_RUN_ID not in stored.payload
    assert before == after == 1


async def test_project_backed_unstaged_autopilot_is_staged_not_adopted(
    engine: AsyncEngine,
) -> None:
    """Scenario: Dispatcher-grace expiry stages the existing autopilot identity."""
    sessions = _sessions(engine)
    topic_id, autopilot_id, project_id = uuid4(), uuid4(), str(uuid4())
    async with sessions() as session:
        await _seed_topic(session, topic_id)
        session.add_all([
            project_row(project_id),
            _autopilot(
                topic_id,
                autopilot_id,
                AutopilotRunState.GENERATING,
                carousel_project_id=project_id,
            ),
        ])
        await session.commit()
        result = await build_manual_recovery(session, RecordingNotifier()).reprocess(
            _command(None, project_id)
        )
        stored = await session.get(GenerationRunModel, result.run.id)
    assert result.outcome is RecoveryOutcome.QUEUED
    assert stored is not None
    assert stored.kind == GenerationKind.AUTOPILOT_DRIVE.value
    assert stored.autopilot_run_id == str(autopilot_id)
    assert stored.dedupe_key == f"autopilot:{autopilot_id}"
    assert stored.payload[PAYLOAD_MANUAL_ORIGIN] == "carousel_reprocess"


async def test_concurrent_failed_terminal_clicks_share_the_successor(
    engine: AsyncEngine,
) -> None:
    """Scenario: Double click returns the existing manual run"""
    sessions = _sessions(engine)
    topic_id, autopilot_id, generation_id = uuid4(), uuid4(), uuid4()
    old = autopilot_run_row(
        autopilot_id, GenerationStatus.DEAD_LETTER, id=generation_id
    )
    async with sessions() as session:
        await _seed_topic(session, topic_id)
        session.add_all([
            _autopilot(topic_id, autopilot_id, AutopilotRunState.FAILED),
            old,
        ])
        await session.commit()
    notifier = RecordingNotifier()
    async with sessions() as first_session, sessions() as second_session:
        first = build_manual_recovery(first_session, notifier)
        second = build_manual_recovery(second_session, notifier)
        results = await asyncio.gather(
            first.reprocess(_command(generation_id)),
            second.reprocess(_command(generation_id)),
        )
    async with sessions() as session:
        audits = await reprocess_audits(session)
        autopilot_rows = list((await session.scalars(select(AutopilotRunModel))).all())
    assert {result.outcome for result in results} == {
        RecoveryOutcome.QUEUED,
        RecoveryOutcome.EXISTING,
    }
    assert len({result.run.id for result in results}) == 1
    assert len(autopilot_rows) == 2
    assert len(audits) == 1
    assert len(notifier.notices) == 2
