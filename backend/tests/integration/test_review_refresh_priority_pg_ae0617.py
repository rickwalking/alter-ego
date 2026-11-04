"""A final-review refresh against real PgQueuer ordering, on Postgres.

Feature: backend/tests/features/review_refresh_priority_ae0617.feature
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.types import QueueEntrypoint, QueueManagerId
from pgqueuer.ports.repository import EntrypointExecutionParameter
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.modules.generation_queue.application.dispatcher import (
    Dispatcher,
    DispatcherDependencies,
)
from rag_backend.modules.generation_queue.constants import (
    ENTRYPOINT,
    ORDINARY_PRIORITY,
    REVIEW_REFRESH_PRIORITY,
)
from rag_backend.modules.generation_queue.domain.models import autopilot_stage
from rag_backend.modules.generation_queue.domain.priority import priority_of
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    PgQueuerJobQueue,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from tests.integration.pg_schema_support import requires_postgres
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeNotices,
)

pytestmark = [pytest.mark.integration, requires_postgres]

PG_URL = os.environ.get("DATABASE_URL", "")
DSN = PG_URL.replace("+asyncpg", "", 1)
_LIST_LIMIT = 10
_NO_LIMIT = 0
_JOB_SQL = "SELECT status, priority, execute_after FROM pgqueuer WHERE id = $1"
_DELAY_SQL = "UPDATE pgqueuer SET execute_after = NOW() + INTERVAL '1 hour' WHERE id=$1"


@dataclass
class _Harness:
    queries: Queries
    store: SqlGenerationRunStore
    queue: PgQueuerJobQueue
    active: FakeActiveAutopilot

    async def dispatch(self) -> None:
        """One real dispatcher pass."""
        await Dispatcher(
            DispatcherDependencies(
                store=self.store,
                queue=self.queue,
                autopilot=self.active,
                notices=FakeNotices(),
            )
        ).run_once()

    async def drive(self, run_id: str) -> tuple[UUID, int]:
        """Stage and hand over an ordinary drive: (generation run, job id)."""
        stage = autopilot_stage(run_id, f"project-{run_id}")
        self.active.runs = [(run_id, stage.carousel_project_id)]
        await self.dispatch()
        self.active.runs = []
        return await self.stored(stage.dedupe_key)

    async def stored(self, dedupe_key: str) -> tuple[UUID, int]:
        """The handed-over run carrying ``dedupe_key``: (generation run, job id)."""
        runs = await self.store.dispatched_active(_LIST_LIMIT)
        [run] = [run for run in runs if run.dedupe_key == dedupe_key]
        assert run.pgq_job_id is not None
        return run.id, run.pgq_job_id

    def refresh(self, run_id: str) -> None:
        """From the next pass on, ``run_id`` only owes the final-review refresh."""
        self.active.refreshes = [(run_id, f"project-{run_id}")]

    async def pick(self) -> int:
        """The job a worker with one slot picks next."""
        jobs = await self.queries.dequeue(
            batch_size=1,
            entrypoints={
                QueueEntrypoint(ENTRYPOINT): EntrypointExecutionParameter(_NO_LIMIT)
            },
            queue_manager_id=QueueManagerId(uuid4()),
            global_concurrency_limit=None,
            heartbeat_timeout=timedelta(seconds=300),
        )
        return int(jobs[0].id)

    async def job(self, job_id: int) -> asyncpg.Record:
        rows = await self.queries.driver.fetch(_JOB_SQL, job_id)
        return rows[0]


@pytest_asyncio.fixture(loop_scope="function")
async def harness() -> AsyncIterator[_Harness]:
    schema = f"pgq_{uuid4().hex[:12]}"
    admin = await asyncpg.connect(DSN)
    await admin.execute(f'CREATE SCHEMA "{schema}"')
    connection = await asyncpg.connect(DSN, server_settings={"search_path": schema})
    engine: AsyncEngine = create_async_engine(
        PG_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        queries = Queries(AsyncpgDriver(connection))
        await queries.install(create_schema=False)
        async with engine.begin() as sql:
            await sql.run_sync(GenerationRunModel.__table__.create, checkfirst=True)
        sessions = async_sessionmaker[AsyncSession](engine, expire_on_commit=False)
        yield _Harness(
            queries,
            SqlGenerationRunStore(sessions),
            PgQueuerJobQueue(queries),
            FakeActiveAutopilot(),
        )
    finally:
        await engine.dispose()
        await connection.close()
        await admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
        await admin.close()


async def test_a_new_refresh_is_picked_before_older_drives(harness: _Harness) -> None:
    """Scenario: A refresh drive is picked before older ordinary drives"""
    _, first = await harness.drive("full-1")
    _, second = await harness.drive("full-2")
    harness.refresh("refresh")
    await harness.dispatch()
    _, refresh = await harness.stored("autopilot:refresh")
    assert await harness.pick() == refresh
    assert await harness.pick() == first
    assert await harness.pick() == second


async def test_a_drive_staged_earlier_is_raised_and_keeps_its_job(
    harness: _Harness,
) -> None:
    """Scenario: A drive staged before the run became a refresh is raised"""
    _, first = await harness.drive("full-1")
    run_id, held = await harness.drive("held")
    harness.refresh("held")
    await harness.dispatch()
    await harness.dispatch()
    run = await harness.store.get(run_id)
    assert run is not None
    assert run.pgq_job_id == held
    assert priority_of(run.payload) == REVIEW_REFRESH_PRIORITY
    assert run.payload["autopilot_run_id"] == "held"
    assert await harness.pick() == held
    assert await harness.pick() == first


async def test_a_raise_keeps_the_retry_delay(harness: _Harness) -> None:
    """Scenario: A raised drive waiting for its render keeps its delay"""
    _, job_id = await harness.drive("waiting")
    await harness.queries.driver.execute(_DELAY_SQL, job_id)
    before = await harness.job(job_id)
    harness.refresh("waiting")
    await harness.dispatch()
    after = await harness.job(job_id)
    assert after["priority"] == REVIEW_REFRESH_PRIORITY
    assert after["execute_after"] == before["execute_after"]


async def test_a_running_drive_is_not_interrupted(harness: _Harness) -> None:
    """Scenario: A running drive is not interrupted"""
    running_id, running_job = await harness.drive("full-1")
    assert await harness.pick() == running_job
    assert await harness.store.mark_running(running_id) is not None
    _, older = await harness.drive("full-2")
    harness.refresh("refresh")
    await harness.dispatch()
    job = await harness.job(running_job)
    assert job["status"] == "picked"
    assert job["priority"] == ORDINARY_PRIORITY
    run = await harness.store.get(running_id)
    assert run is not None
    assert run.status.value == "running"
    assert priority_of(run.payload) == ORDINARY_PRIORITY
    picked = await harness.pick()
    assert picked not in (running_job, older)
    assert await harness.pick() == older


async def test_a_running_refresh_drive_stays_as_it_is(harness: _Harness) -> None:
    """Scenario: A refresh drive that is itself running is left alone"""
    run_id, job_id = await harness.drive("self")
    assert await harness.pick() == job_id
    assert await harness.store.mark_running(run_id) is not None
    harness.refresh("self")
    await harness.dispatch()
    job = await harness.job(job_id)
    assert (job["status"], job["priority"]) == ("picked", ORDINARY_PRIORITY)
    run = await harness.store.get(run_id)
    assert run is not None
    assert priority_of(run.payload) == ORDINARY_PRIORITY


async def test_a_rework_with_work_left_keeps_fifo(harness: _Harness) -> None:
    """Scenario Outline: A rework with work left keeps FIFO"""
    _, first = await harness.drive("full-1")
    _, second = await harness.drive("content-rework")
    await harness.dispatch()
    assert (await harness.job(second))["priority"] == ORDINARY_PRIORITY
    assert await harness.pick() == first
    assert await harness.pick() == second
