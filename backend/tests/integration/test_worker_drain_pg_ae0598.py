"""The deploy drain against real PgQueuer on Postgres.

A drained worker hands the picked job back to PgQueuer without touching the run;
once the flag is cleared the same job is claimed and the run succeeds.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from pgqueuer import PgQueuer
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.errors import RetryRequested
from pgqueuer.domain.models import Job
from pgqueuer.domain.types import QueueExecutionMode
from sqlalchemy import text
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
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
)
from rag_backend.modules.generation_queue.constants import ENTRYPOINT
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome, StepTracker
from rag_backend.modules.generation_queue.infrastructure import schema
from rag_backend.modules.generation_queue.infrastructure.drive_lock import (
    DriveLockTiming,
    PostgresDriveLock,
)
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    PgQueuerJobQueue,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    asyncpg_connection,
)
from rag_backend.modules.generation_queue.infrastructure.repository import (
    SqlGenerationRunStore,
)
from rag_backend.worker import main
from rag_backend.worker.drain import DrainFiles, DrainSwitch, JobGate
from tests.integration.pg_schema_support import PG_URL, requires_postgres
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeActiveAutopilot,
    FakeNotices,
    FixedClock,
)

pytestmark = [
    pytest.mark.integration,
    requires_postgres,
    pytest.mark.asyncio(loop_scope="function"),
]

_FAST_LOCK = DriveLockTiming(wait_seconds=0.3, poll_seconds=0.05, watch_seconds=0.05)
_SHORT_DELAY = timedelta(seconds=1)


@pytest_asyncio.fixture(loop_scope="function")
async def engine() -> AsyncIterator[AsyncEngine]:
    name = f"gqd_{uuid4().hex[:12]}"
    admin = create_async_engine(PG_URL)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{name}"'))
    scoped = create_async_engine(
        PG_URL, connect_args={"server_settings": {"search_path": name}}
    )
    async with scoped.begin() as conn:
        await conn.execute(
            text("CREATE TABLE carousel_projects (id VARCHAR(36) PRIMARY KEY)")
        )
    try:
        yield scoped
    finally:
        await scoped.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
        await admin.dispose()


class _Executor:
    """Counts the runs it executed."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        return [f"run:{run.autopilot_run_id}"]

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        await tracker.begin("start")
        self.executed.append(str(run.autopilot_run_id))
        await tracker.finish("start")
        return StepOutcome.DONE


async def _status(engine: AsyncEngine) -> tuple[str, int]:
    async with engine.connect() as conn:
        row = (
            await conn.execute(text("SELECT status, attempts FROM generation_runs"))
        ).one()
    return str(row[0]), int(row[1])


async def test_a_drained_worker_puts_the_job_back_and_claims_it_after_clear(
    engine: AsyncEngine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A drained worker refuses to claim a job and puts it back"""
    monkeypatch.setattr(main, "DRAIN_RETRY_DELAY", _SHORT_DELAY)
    await schema.apply(engine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    store = SqlGenerationRunStore(sessions)
    executor = _Executor()
    handler = GenerationJobHandler(
        HandlerDependencies(
            store=store,
            lock=PostgresDriveLock(engine, _FAST_LOCK),
            executors={GenerationKind.AUTOPILOT_DRIVE: executor},
            notices=FakeNotices(),
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
        )
    )
    switch = DrainSwitch(DrainFiles(drain=tmp_path / "drain", busy=tmp_path / "busy"))
    switch.request()
    async with asyncpg_connection(engine) as connection:
        pgq = PgQueuer(AsyncpgDriver(connection))
        entry = main.job_entrypoint(handler, JobGate(switch))
        refused = asyncio.Event()

        async def watched(job: Job) -> None:
            try:
                await entry(job)
            except RetryRequested:
                refused.set()
                raise

        pgq.entrypoint(ENTRYPOINT, concurrency_limit=1, on_failure="hold")(watched)
        await Dispatcher(
            DispatcherDependencies(
                store=store,
                queue=PgQueuerJobQueue(Queries(pgq.connection)),
                autopilot=FakeActiveAutopilot(runs=[("r1", None)]),
                notices=FakeNotices(),
            )
        ).run_once()
        worker = asyncio.create_task(pgq.run(batch_size=1))
        await asyncio.wait_for(refused.wait(), timeout=30)
        pgq.shutdown.set()
        await asyncio.wait_for(worker, timeout=30)
        assert executor.executed == []
        assert await _status(engine) == ("queued", 0)
        async with engine.connect() as conn:
            queued = await conn.scalar(
                text("SELECT count(*) FROM pgqueuer WHERE status = 'queued'")
            )
        assert queued == 1
        assert not switch.is_busy()
        # Scenario: The worker claims jobs again once the drain is cleared
        switch.clear()
        await asyncio.sleep(_SHORT_DELAY.total_seconds() + 0.5)
        pgq.shutdown.clear()
        await asyncio.wait_for(
            pgq.run(mode=QueueExecutionMode.drain, batch_size=1), timeout=30
        )
    assert executor.executed == ["r1"]
    assert (await _status(engine))[0] == "succeeded"
