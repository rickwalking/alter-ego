""" "Tentar de novo" through the webhook service on a real database (Postgres in CI).

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
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
_DEAD = "queue_dead_letter:run_budget_exhausted"
_PARKED_AT = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)


class _Claims:
    async def claim_update(self, update: object) -> bool:
        del update
        return True


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with queue_flow_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


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


async def _tap_retry(engine: AsyncEngine, run_id: UUID, update_id: int) -> list[str]:
    messenger = _Messenger()
    async with _sessions(engine)() as session:
        repo = SqlAlchemyAutopilotRepository(session)
        service = OwnerActionService(
            OwnerActionDeps(
                runs=repo,
                updates=_Claims(),
                pending=_Pending(),
                editorial=_Editorial(),
                release=_Release(),
                messenger=messenger,
                recovery=_Recovery(runs=repo),
                clock=_Clock(),
                owner_chat_id=_OWNER,
                topics=repo,
                queue=SqlQueueControl(session),
                dead_letters=SqlDeadLetterRuns(session),
            )
        )
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
    assert run is not None
    assert row is not None
    assert (run.state, run.state_reason) == ("generating", REASON_DEAD_RETRY)
    assert row.status == "queued"
    assert row.pgq_job_id is None
    assert row.phase_attempts == {"content": 1}
    assert row.attempts == 1
    assert row.created_at.replace(tzinfo=UTC) > _PARKED_AT
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
