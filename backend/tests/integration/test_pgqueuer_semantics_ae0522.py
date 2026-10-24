"""PgQueuer semantics gate, against the pinned 1.6.0 source (ADR-0026).

Each test pins one behaviour the queue relies on; a PgQueuer upgrade that changes
it fails here before it reaches prod. Every test runs in a throwaway schema with
PgQueuer installed by the same ``install`` call the deploy one-shot uses.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from pgqueuer.adapters.drivers.asyncpg import AsyncpgDriver
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.models import CronExpressionEntrypoint, TracebackRecord
from pgqueuer.domain.types import (
    CronEntrypoint,
    CronExpression,
    QueueEntrypoint,
    QueueManagerId,
)
from pgqueuer.ports.repository import EntrypointExecutionParameter

from tests.integration.pg_schema_support import requires_postgres

pytestmark = [pytest.mark.integration, requires_postgres]

ENTRYPOINT = "carousel_generation"
DSN = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "", 1)
LIMIT_ONE = {QueueEntrypoint(ENTRYPOINT): EntrypointExecutionParameter(1)}
UNLIMITED = {QueueEntrypoint(ENTRYPOINT): EntrypointExecutionParameter(0)}
HEARTBEAT = timedelta(seconds=300)


@pytest_asyncio.fixture(loop_scope="function")
async def queries() -> AsyncIterator[Queries]:
    schema = f"pgq_{uuid4().hex[:12]}"
    admin = await asyncpg.connect(DSN)
    await admin.execute(f'CREATE SCHEMA "{schema}"')
    connection = await asyncpg.connect(DSN, server_settings={"search_path": schema})
    try:
        installed = Queries(AsyncpgDriver(connection))
        await installed.install(create_schema=False)
        yield installed
    finally:
        await connection.close()
        await admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
        await admin.close()


async def _dequeue(
    queries: Queries,
    entrypoints: dict[QueueEntrypoint, EntrypointExecutionParameter] = LIMIT_ONE,
    heartbeat: timedelta = HEARTBEAT,
) -> list[int]:
    jobs = await queries.dequeue(
        batch_size=10,
        entrypoints=entrypoints,
        queue_manager_id=QueueManagerId(uuid4()),
        global_concurrency_limit=None,
        heartbeat_timeout=heartbeat,
    )
    return [int(job.id) for job in jobs]


async def _hold(queries: Queries, job_id: int) -> None:
    (job,) = [job for job in await queries.browse_queue(10, 0) if job.id == job_id]
    record = TracebackRecord.from_exception(
        exc=RuntimeError("boom"), job_id=job.id, additional_context={}
    )
    await queries.log_jobs([(job, "failed", record)])


async def _status(queries: Queries, job_id: int) -> str | None:
    job = await queries.queue_job_by_id(job_id)
    return None if job is None else str(job.status)


async def test_held_job_does_not_block_a_new_job_with_the_same_key(
    queries: Queries,
) -> None:
    """Scenario: PgQueuer keeps a held job apart from a new job with the same dedupe key"""
    (first,) = await queries.enqueue(ENTRYPOINT, b"a", dedupe_key="k")
    assert await _dequeue(queries) == [first]
    await _hold(queries, first)
    assert await _status(queries, first) == "failed"
    (second,) = await queries.enqueue(ENTRYPOINT, b"b", dedupe_key="k")
    assert second != first
    skipped = await queries.enqueue(
        ENTRYPOINT, b"c", dedupe_key="k", on_conflict="skip"
    )
    assert skipped == [None]
    with pytest.raises(asyncpg.UniqueViolationError):
        await queries.requeue_jobs([first])
    await queries.mark_job_as_cancelled([second])
    await queries.requeue_jobs([first])
    assert await _status(queries, first) == "queued"


async def test_delayed_enqueue_waits_for_execute_after(queries: Queries) -> None:
    """Scenario: PgQueuer delays a job until its execute_after"""
    (job,) = await queries.enqueue(ENTRYPOINT, b"a", execute_after=timedelta(seconds=1))
    assert await _dequeue(queries) == []
    await asyncio.sleep(1.2)
    assert await _dequeue(queries) == [job]


async def test_stale_heartbeat_repick_counts_no_attempt(queries: Queries) -> None:
    """Scenario: PgQueuer re-picks a job after the configured heartbeat timeout without counting an attempt"""
    (job,) = await queries.enqueue(ENTRYPOINT, b"a")
    assert await _dequeue(queries) == [job]
    assert await _dequeue(queries, heartbeat=timedelta(seconds=300)) == []
    await asyncio.sleep(1.1)
    assert await _dequeue(queries, heartbeat=timedelta(seconds=1)) == [job]
    picked = await queries.queue_job_by_id(job)
    assert picked is not None
    assert picked.attempts == 0


async def test_fifo_under_a_concurrency_limit_of_one(queries: Queries) -> None:
    """Scenario: PgQueuer dequeues in FIFO order under a concurrency limit of 1"""
    ids = [
        (await queries.enqueue(ENTRYPOINT, f"{index}".encode()))[0]
        for index in range(3)
    ]
    first = await _dequeue(queries)
    assert first == [ids[0]]
    assert await _dequeue(queries) == []
    (picked,) = [job for job in await queries.browse_queue(10, 0) if job.id == ids[0]]
    await queries.log_jobs([(picked, "successful", None)])
    assert await _dequeue(queries) == [ids[1]]
    assert sorted(await _dequeue(queries, UNLIMITED)) == [ids[2]]


async def test_held_job_requeue_resets_attempts(queries: Queries) -> None:
    """Scenario: PgQueuer requeues a held job"""
    (job,) = await queries.enqueue(ENTRYPOINT, b"a")
    await _dequeue(queries)
    (picked,) = await queries.browse_queue(10, 0)
    await queries.retry_job(picked, timedelta(0), None)
    assert (await queries.queue_job_by_id(job)).attempts == 1
    await _dequeue(queries)
    await _hold(queries, job)
    assert [int(held.id) for held in await queries.list_failed_jobs(10)] == [job]
    await queries.requeue_jobs([job])
    requeued = await queries.queue_job_by_id(job)
    assert str(requeued.status) == "queued"
    assert requeued.attempts == 0
    assert await _dequeue(queries) == [job]


async def test_a_schedule_is_claimed_once_across_workers(queries: Queries) -> None:
    """Scenario: PgQueuer fires a schedule once across workers"""
    entry = CronExpressionEntrypoint(
        CronEntrypoint("daily_scan"), CronExpression("0 7 * * *")
    )
    await queries.insert_schedule({entry: timedelta(0)})
    await queries.insert_schedule({entry: timedelta(0)})
    assert len(await queries.peek_schedule()) == 1
    claims = await asyncio.gather(
        queries.fetch_schedule({entry: timedelta(days=1)}),
        queries.fetch_schedule({entry: timedelta(days=1)}),
    )
    assert sorted(len(claim) for claim in claims) == [0, 1]


async def test_log_rows_can_be_purged_by_age(queries: Queries) -> None:
    """Scenario: PgQueuer log rows can be purged by age"""
    (job,) = await queries.enqueue(ENTRYPOINT, b"a")
    (recent,) = await queries.enqueue(ENTRYPOINT, b"b")
    assert queries.qbe.settings.qualified.queue_table_log == "pgqueuer_log"
    await queries.driver.execute(
        "UPDATE pgqueuer_log SET created = NOW() - interval '31 days'"
        " WHERE job_id = $1",
        job,
    )
    await queries.driver.execute(
        "DELETE FROM pgqueuer_log WHERE created < NOW() - interval '30 days'"
    )
    rows = await queries.driver.fetch("SELECT job_id FROM pgqueuer_log")
    assert [int(str(row["job_id"])) for row in rows] == [recent]
    await queries.aggregate_logs()
