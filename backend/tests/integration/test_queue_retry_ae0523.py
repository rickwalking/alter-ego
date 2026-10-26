""" "Tentar de novo" through the webhook service on a real database (Postgres in CI).

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.dead_letter_runs import (
    SqlDeadLetterRuns,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TelegramUpdateModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.queue_constants import (
    CALLBACK_DEAD_RETRY_PREFIX,
    REASON_DEAD_RETRY,
    TEXT_QUEUE_ALREADY,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.manual_reprocess_support import (
    RecordingNotifier,
    reprocess_audits,
)
from tests.integration.queue_flow_db_support import queue_flow_engine
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _Clock,
    _Editorial,
    _Messenger,
    _Pending,
    _Release,
    _tap,
)

_OWNER = "42"
_OWNER_USER = "00000000-0000-0000-0000-000000000042"
_DEAD = "queue_dead_letter:run_budget_exhausted"
_PARKED_AT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _begin_outer(session: AsyncSession) -> None:
    if session.bind is not None and session.bind.dialect.name == "sqlite":
        await session.execute(text("BEGIN"))
        return
    await session.execute(select(1))


async def _parked(engine: AsyncEngine) -> tuple[UUID, UUID]:
    topic_id, run_id, dead_id = uuid4(), uuid4(), uuid4()
    async with _sessions(engine)() as session:
        session.add(
            TopicCandidateModel(
                id=topic_id,
                title="Agentes",
                angle="a",
                why_viral="w",
                audience="a",
                niche="n",
                brief="b",
                sources=["https://example.com/a"],
                score=80,
                signal_hash=uuid4().hex,
                status="promoted",
            )
        )
        await session.flush()
        session.add(
            AutopilotRunModel(
                id=run_id,
                topic_candidate_id=topic_id,
                state=AutopilotRunState.ESCALATED.value,
                state_reason=_DEAD,
                publish_attempts=0,
                telegram_message_ids=[],
                created_at=_PARKED_AT,
                updated_at=_PARKED_AT,
            )
        )
        session.add(
            GenerationRunModel(
                id=dead_id,
                kind="autopilot_drive",
                dedupe_key=f"autopilot:{run_id}",
                status="dead_letter",
                payload={"autopilot_run_id": str(run_id)},
                autopilot_run_id=str(run_id),
                attempts=4,
                phase_attempts={"images": 3, "content": 1},
                last_phase="images",
                last_error_code="run_budget_exhausted",
                created_at=_PARKED_AT - timedelta(hours=1),
                started_at=_PARKED_AT - timedelta(hours=1),
                finished_at=_PARKED_AT,
                updated_at=_PARKED_AT,
            )
        )
        await session.commit()
    return run_id, dead_id


def _owner_service(
    session: AsyncSession, messenger: _Messenger, notifier: RecordingNotifier
) -> OwnerActionService:
    repo = SqlAlchemyAutopilotRepository(session)
    return OwnerActionService(
        OwnerActionDeps(
            runs=repo,
            updates=repo,
            pending=_Pending(),
            editorial=_Editorial(),
            release=_Release(),
            messenger=messenger,
            recovery=_Recovery(runs=repo),
            clock=_Clock(),
            owner_chat_id=_OWNER,
            owner_user_id=_OWNER_USER,
            topics=repo,
            queue=SqlQueueControl(session, notifier, deferred=True),
            dead_letters=SqlDeadLetterRuns(session),
        )
    )


async def _tap_retry(engine: AsyncEngine, run_id: UUID, update_id: int) -> list[str]:
    messenger = _Messenger()
    async with _sessions(engine)() as session:
        service = _owner_service(session, messenger, RecordingNotifier())
        await _begin_outer(session)
        await service.handle(_tap(update_id, f"{CALLBACK_DEAD_RETRY_PREFIX}{run_id}"))
        await session.commit()
        await service.deliver()
    return [edit.text for edit in messenger.edits]


async def test_retry_resumes_an_escalated_dead_letter_on_the_database(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry resumes a run that died mid-generation"""
    run_id, dead_id = await _parked(engine)
    said = await _tap_retry(engine, run_id, 1)
    async with _sessions(engine)() as session:
        run = await session.get(AutopilotRunModel, run_id)
        row = await session.get(GenerationRunModel, dead_id)
        audits = await reprocess_audits(session)
    assert run is not None
    assert row is not None
    assert (run.state, run.state_reason) == ("generating", REASON_DEAD_RETRY)
    assert row.status == "queued"
    assert row.pgq_job_id is None
    assert row.phase_attempts == {"content": 1}
    assert row.attempts == 1
    assert row.payload["manual_priority"] == 1
    assert row.payload["manual_origin"] == "carousel_reprocess"
    assert row.created_at.replace(tzinfo=UTC) > _PARKED_AT
    assert len(audits) == 1
    assert audits[0].payload["actor_id"] == _OWNER_USER
    assert audits[0].payload["actor_id"] != _OWNER
    assert said[-1].startswith("🔁 De volta à fila. Na fila: posição 1 de 1")


async def test_retry_happens_once_on_the_database(engine: AsyncEngine) -> None:
    """Scenario: Retry happens once"""
    run_id, dead_id = await _parked(engine)
    await _tap_retry(engine, run_id, 1)
    said = await _tap_retry(engine, run_id, 2)
    async with _sessions(engine)() as session:
        row = await session.get(GenerationRunModel, dead_id)
    assert row is not None
    assert row.status == "queued"
    assert said[-1] == TEXT_QUEUE_ALREADY


async def test_retry_callback_claim_rolls_back_with_recovery(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry callback claim and recovery share one transaction"""
    run_id, dead_id = await _parked(engine)
    update_id = 77
    notifier = RecordingNotifier()
    async with _sessions(engine)() as session:
        service = _owner_service(session, _Messenger(), notifier)
        await _begin_outer(session)
        await service.handle(_tap(update_id, f"{CALLBACK_DEAD_RETRY_PREFIX}{run_id}"))
        await session.rollback()
        service.discard()
    async with _sessions(engine)() as session:
        claim = await session.get(TelegramUpdateModel, update_id)
        run = await session.get(AutopilotRunModel, run_id)
        row = await session.get(GenerationRunModel, dead_id)
        audits = await reprocess_audits(session)
    assert claim is None
    assert run is not None and run.state == AutopilotRunState.ESCALATED.value
    assert row is not None and row.status == "dead_letter"
    assert audits == []
    assert notifier.notices == []
    said = await _tap_retry(engine, run_id, update_id)
    async with _sessions(engine)() as session:
        claim = await session.get(TelegramUpdateModel, update_id)
        audits = await reprocess_audits(session)
    assert said
    assert claim is not None
    assert len(audits) == 1


async def test_retry_callback_duplicate_delivery_is_a_noop(
    engine: AsyncEngine,
) -> None:
    """Scenario: Retry callback claim and recovery share one transaction"""
    run_id, _ = await _parked(engine)
    update_id = 88
    first = await _tap_retry(engine, run_id, update_id)
    second = await _tap_retry(engine, run_id, update_id)
    async with _sessions(engine)() as session:
        audits = await reprocess_audits(session)
    assert first
    assert second == []
    assert len(audits) == 1
