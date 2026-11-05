"""The SQL store raises a waiting run and leaves a running one, on SQLite.

Feature: backend/tests/features/review_refresh_priority_ae0617.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rag_backend.infrastructure.database.config import Base
from rag_backend.modules.generation_queue.constants import (
    ORDINARY_PRIORITY,
    REVIEW_REFRESH_PRIORITY,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationRun,
    GenerationStatus,
    RetryCommand,
    autopilot_stage,
)
from rag_backend.modules.generation_queue.domain.priority import priority_of
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from tests.unit.modules.generation_queue.queue_fakes import NOW, FixedClock

_RUN = "r1"
_KEY = autopilot_stage(_RUN).dedupe_key


@pytest.fixture
async def store() -> AsyncIterator[SqlGenerationRunStore]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all, tables=[GenerationRunModel.__table__]
        )
    sessions = async_sessionmaker[AsyncSession](engine, expire_on_commit=False)
    yield SqlGenerationRunStore(sessions, FixedClock())
    await engine.dispose()


async def _staged(store: SqlGenerationRunStore) -> UUID:
    await store.stage(autopilot_stage(_RUN, "p1"))
    [run] = await store.undispatched(1)
    return run.id


async def _stored(store: SqlGenerationRunStore, run_id: UUID) -> GenerationRun:
    run = await store.get(run_id)
    assert run is not None
    return run


async def test_a_queued_run_is_raised_and_keeps_its_job(
    store: SqlGenerationRunStore,
) -> None:
    """Scenario: A drive staged before the run became a refresh is raised"""
    run_id = await _staged(store)
    await store.set_job(run_id, 7)
    raised = await store.raise_priority(_KEY, REVIEW_REFRESH_PRIORITY)
    assert raised is not None
    assert (raised.id, raised.pgq_job_id) == (run_id, 7)
    assert priority_of(raised.payload) == REVIEW_REFRESH_PRIORITY
    stored = await _stored(store, run_id)
    assert priority_of(stored.payload) == REVIEW_REFRESH_PRIORITY
    assert stored.payload["autopilot_run_id"] == _RUN


async def test_a_run_in_retry_wait_is_raised(store: SqlGenerationRunStore) -> None:
    """Scenario: A raised drive waiting for its render keeps its delay"""
    run_id = await _staged(store)
    attempt_id = await store.mark_running(run_id)
    assert attempt_id is not None
    await store.mark_waiting(
        RetryCommand(
            run_id=run_id,
            attempt_id=attempt_id,
            next_attempt_at=NOW + timedelta(seconds=60),
            error_code="waiting",
            error="",
        )
    )
    raised = await store.raise_priority(_KEY, REVIEW_REFRESH_PRIORITY)
    assert raised is not None
    assert raised.status is GenerationStatus.RETRY_WAIT
    assert raised.payload[ATTEMPT_ID_KEY] == str(attempt_id)


async def test_a_running_run_is_not_touched(store: SqlGenerationRunStore) -> None:
    """Scenario: A refresh drive that is itself running is left alone"""
    run_id = await _staged(store)
    attempt_id = await store.mark_running(run_id)
    assert await store.raise_priority(_KEY, REVIEW_REFRESH_PRIORITY) is None
    stored = await _stored(store, run_id)
    assert priority_of(stored.payload) == ORDINARY_PRIORITY
    assert stored.status is GenerationStatus.RUNNING
    assert stored.payload[ATTEMPT_ID_KEY] == str(attempt_id)


async def test_no_run_under_the_key(store: SqlGenerationRunStore) -> None:
    """Scenario: A drive staged before the run became a refresh is raised"""
    assert await store.raise_priority("autopilot:none", 1) is None
