"""Pinned PgQueuer priority, kick, cancellation and maintenance semantics."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.models import Job
from pgqueuer.domain.types import QueueEntrypoint, QueueManagerId
from pgqueuer.ports.repository import EntrypointExecutionParameter
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.modules.generation_queue.constants import (
    ENTRYPOINT,
    MAINTENANCE_ENTRYPOINT,
    PAYLOAD_MANUAL_ACCELERATE_JOB_ID,
    PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID,
    PAYLOAD_MANUAL_CANCEL_JOB_ID,
    PAYLOAD_MANUAL_PRIORITY,
)
from rag_backend.modules.generation_queue.domain.maintenance import MaintenanceCommand
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    MaintenanceNotice,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationRun,
    GenerationStatus,
)
from rag_backend.modules.generation_queue.infrastructure import maintenance_gateway
from rag_backend.modules.generation_queue.infrastructure.maintenance_gateway import (
    PgQueuerMaintenanceGateway,
    WebMaintenanceGateway,
)
from rag_backend.modules.generation_queue.infrastructure.maintenance_lock import (
    PostgresMaintenanceLock,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    PgQueuerJobQueue,
)
from rag_backend.modules.generation_queue.infrastructure.raw_connection import (
    AsyncpgConnection,
)
from tests.integration.pg_schema_support import requires_postgres
from tests.unit.modules.generation_queue.queue_fakes import make_run

pytestmark = [pytest.mark.integration, requires_postgres]

PG_URL = os.environ.get("DATABASE_URL", "")
DSN = PG_URL.replace("+asyncpg", "", 1)
LIMIT_ONE = {QueueEntrypoint(ENTRYPOINT): EntrypointExecutionParameter(1)}
_DEDUPE_SQL = "SELECT dedupe_key FROM pgqueuer WHERE entrypoint = $1"


@dataclass
class _Harness:
    queries: Queries
    engine: AsyncEngine
    dsn: str
    channel: str


@pytest_asyncio.fixture(loop_scope="function")
async def harness() -> AsyncIterator[_Harness]:
    schema = f"pgq_{uuid4().hex[:12]}"
    admin = await asyncpg.connect(DSN)
    await admin.execute(f'CREATE SCHEMA "{schema}"')
    connection = await asyncpg.connect(DSN, server_settings={"search_path": schema})
    engine = create_async_engine(
        PG_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        queries = Queries(AsyncpgDriver(connection))
        await queries.install(create_schema=False)
        async with engine.begin() as sql:
            await sql.run_sync(GenerationRunModel.__table__.create, checkfirst=True)
        yield _Harness(queries, engine, DSN, queries.qbe.settings.channel)
    finally:
        await engine.dispose()
        await connection.close()
        await admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
        await admin.close()


def _manual(name: str) -> GenerationRun:
    return make_run(
        dedupe_key=name,
        payload={"autopilot_run_id": name, PAYLOAD_MANUAL_PRIORITY: 1},
    )


async def _dequeue(queries: Queries) -> list[int]:
    jobs = await queries.dequeue(
        batch_size=1,
        entrypoints=LIMIT_ONE,
        queue_manager_id=QueueManagerId(uuid4()),
        global_concurrency_limit=None,
        heartbeat_timeout=timedelta(seconds=300),
    )
    return [int(job.id) for job in jobs]


async def _finish(queries: Queries, job_id: int) -> None:
    job = await queries.queue_job_by_id(job_id)
    assert job is not None
    await queries.log_jobs([(job, "successful", None)])


async def _persist(harness: _Harness, run: GenerationRun) -> None:
    now = run.created_at or datetime.now(UTC)
    row = GenerationRunModel(
        id=run.id,
        kind=run.kind.value,
        dedupe_key=run.dedupe_key,
        status=run.status.value,
        payload=run.payload,
        autopilot_run_id=run.autopilot_run_id,
        pgq_job_id=run.pgq_job_id,
        attempts=0,
        phase_attempts={},
        created_at=now,
        updated_at=now,
    )
    async with async_sessionmaker(harness.engine)() as session:
        session.add(row)
        await session.commit()


async def _picked(harness: _Harness, run: GenerationRun) -> int:
    job_id = await PgQueuerJobQueue(harness.queries).enqueue(run)
    assert job_id is not None
    assert await _dequeue(harness.queries) == [job_id]
    return job_id


def _recovered(run: GenerationRun, job_id: int, attempt: UUID) -> GenerationRun:
    payload = {
        **run.payload,
        ATTEMPT_ID_KEY: str(uuid4()),
        PAYLOAD_MANUAL_CANCEL_JOB_ID: job_id,
        PAYLOAD_MANUAL_CANCEL_ATTEMPT_ID: str(attempt),
    }
    return replace(run, pgq_job_id=job_id, payload=payload)


async def _job(queries: Queries, job_id: int) -> Job:
    job = await queries.queue_job_by_id(job_id)
    assert job is not None
    return job


async def _dedupe_keys(harness: _Harness) -> set[str]:
    rows = await harness.queries.driver.fetch(_DEDUPE_SQL, MAINTENANCE_ENTRYPOINT)
    return {str(row["dedupe_key"]) for row in rows}


async def _finish_next(queries: Queries, previous: int, following: int) -> None:
    await _finish(queries, previous)
    assert await _dequeue(queries) == [following]


async def test_manual_priority_is_fifo_and_never_preempts_or_demotes(
    harness: _Harness,
) -> None:
    """Scenario: Manual recovery keeps class FIFO behind the active drive."""
    queue = PgQueuerJobQueue(harness.queries)
    active_id = await _picked(harness, make_run(dedupe_key="active"))
    first, ordinary, second = (
        _manual("first"),
        make_run(dedupe_key="ordinary"),
        _manual("second"),
    )
    ids = [await queue.enqueue(run) for run in (first, ordinary, second)]
    first_id, ordinary_id, second_id = ids
    demoted = replace(first, payload={"autopilot_run_id": "first"})
    assert await queue.enqueue(demoted) == first_id
    assert str((await _job(harness.queries, active_id)).status) == "picked"
    assert (await _job(harness.queries, first_id)).priority == 1
    await _finish_next(harness.queries, active_id, first_id)
    await _finish_next(harness.queries, first_id, second_id)
    await _finish_next(harness.queries, second_id, ordinary_id)


async def test_retry_kick_updates_queued_priority_and_eligibility(
    harness: _Harness,
) -> None:
    """Scenario: Retry and stale transport jobs use explicit fences"""
    queue = PgQueuerJobQueue(harness.queries)
    run = _manual("retry")
    (job_id,) = await harness.queries.enqueue(
        ENTRYPOINT,
        str(run.id).encode(),
        execute_after=timedelta(hours=1),
        dedupe_key=run.dedupe_key,
    )
    payload = {**run.payload, PAYLOAD_MANUAL_ACCELERATE_JOB_ID: int(job_id)}
    run = replace(run, pgq_job_id=int(job_id), payload=payload)
    assert await queue.kick(run) == int(job_id)
    assert await queue.kick(run) == int(job_id)
    job = await _job(harness.queries, int(job_id))
    assert (job.priority, str(job.status)) == (1, "queued")
    assert job.execute_after <= datetime.now(UTC)
    assert await _dequeue(harness.queries) == [int(job_id)]


async def test_stale_picked_kick_cancels_and_requeues_without_dedupe_block(
    harness: _Harness,
) -> None:
    """Scenario: Retry and stale transport jobs use explicit fences"""
    queue = PgQueuerJobQueue(harness.queries)
    old_attempt = uuid4()
    run = _manual("stale")
    run = replace(run, payload={**run.payload, ATTEMPT_ID_KEY: str(old_attempt)})
    old_id = await _picked(harness, run)
    recovered = _recovered(run, old_id, old_attempt)
    await _persist(harness, recovered)
    new_id = await queue.kick(recovered)
    assert new_id is not None and new_id != old_id
    assert await harness.queries.queue_job_by_id(old_id) is None
    replacement = await _job(harness.queries, new_id)
    assert (replacement.priority, str(replacement.status)) == (1, "queued")
    assert await queue.kick(replace(recovered, pgq_job_id=new_id)) == new_id
    jobs = await harness.queries.browse_queue(10, 0)
    assert [int(job.id) for job in jobs] == [new_id]
    assert await _dequeue(harness.queries) == [new_id]


async def test_picked_kick_does_not_cancel_a_new_active_attempt(
    harness: _Harness,
) -> None:
    """Scenario: A queued snapshot cannot preempt a newly running attempt."""
    queue = PgQueuerJobQueue(harness.queries)
    run = _manual("active-race")
    old_id = await _picked(harness, run)
    stale = _recovered(run, old_id, uuid4())
    active_payload = {**stale.payload, ATTEMPT_ID_KEY: str(uuid4())}
    active = replace(stale, status=GenerationStatus.RUNNING, payload=active_payload)
    await _persist(harness, active)
    assert await queue.kick(stale) == old_id
    job = await _job(harness.queries, old_id)
    assert str(job.status) == "picked"


async def test_full_maintenance_lock_is_non_blocking(harness: _Harness) -> None:
    """Scenario: A second full-pass claimant exits busy until the lock releases."""
    lock = PostgresMaintenanceLock(harness.engine)
    async with lock.hold() as acquired:
        assert acquired is True
        async with lock.hold() as busy:
            assert busy is False
    async with lock.hold() as again:
        assert again is True


async def test_full_control_dedupes_and_insert_notifies(harness: _Harness) -> None:
    """Scenario: Full control jobs share dedupe and wake listeners on insert."""
    gateway = PgQueuerMaintenanceGateway(harness.queries)
    listener = await asyncpg.connect(harness.dsn)
    messages: asyncio.Queue[str] = asyncio.Queue()
    try:
        await listener.add_listener(
            harness.channel, lambda *args: messages.put_nowait(args[-1])
        )
        full = await gateway.request_full()
        event = json.loads(await asyncio.wait_for(messages.get(), timeout=2))
        existing = await gateway.request_full()
        assert event["operation"] == "insert"
        assert (full.inserted, existing.inserted) == (True, False)
        assert existing.job_id == full.job_id
    finally:
        await listener.close()


async def test_web_gateway_closes_its_raw_driver(
    harness: _Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Web maintenance closes the asyncpg handle and socket."""
    seen: list[AsyncpgConnection] = []
    original = maintenance_gateway.asyncpg_connection

    @asynccontextmanager
    async def capture(engine: AsyncEngine) -> AsyncIterator[AsyncpgConnection]:
        async with original(engine) as connection:
            seen.append(connection)
            yield connection

    monkeypatch.setattr(maintenance_gateway, "asyncpg_connection", capture)
    gateway = WebMaintenanceGateway(harness.engine)
    assert await gateway.notify(MaintenanceNotice(run_id=uuid4())) is True
    assert len(seen) == 1
    assert seen[0].is_closed() is True


async def test_dispatch_control_dedupes_for_worker_and_web(
    harness: _Harness,
) -> None:
    """Scenario: Maintenance control jobs are durable and deduped"""
    gateway = PgQueuerMaintenanceGateway(harness.queries)
    notice = MaintenanceNotice(run_id=uuid4())
    assert await gateway.notify(notice) is True
    assert await gateway.notify(notice) is True
    web_notice = MaintenanceNotice(run_id=uuid4())
    web = WebMaintenanceGateway(harness.engine)
    assert await web.notify(web_notice) is True
    assert await web.notify(web_notice) is True
    jobs = await harness.queries.browse_queue(10, 0)
    assert len(jobs) == 2
    assert await _dedupe_keys(harness) == {
        MaintenanceCommand(run_id=notice.run_id).dedupe_key,
        MaintenanceCommand(run_id=web_notice.run_id).dedupe_key,
    }
