"""SQL job repository over in-memory SQLite.

Gherkin: tests/features/image_bridge.feature
  Scenario: The waiter works across processes
  Scenario: Duplicate callback
  Scenario: Grok Bot never answers
The same behaviour on Postgres: tests/integration/test_image_bridge_repository_pg.py
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJobStatus,
    JobDeadline,
    JobFailure,
    JobSuccess,
)
from tests.unit.modules.image_bridge.support import T0, pending_job, sqlite_repository


async def test_create_then_get_round_trips_the_job() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        stored = await repo.get(job.id)
        assert await repo.get(uuid4()) is None
    assert stored == job
    assert stored is not None
    assert stored.created_at.tzinfo is not None


# Scenario: The waiter works across processes
async def test_succeed_stores_bytes_once_and_take_nulls_them() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        assert await repo.succeed(JobSuccess(job.id, b"png", T0)) is True
        stored = await repo.get(job.id)
        first = await repo.take_image(job.id)
        second = await repo.take_image(job.id)
    assert stored is not None
    assert stored.status is ImageBridgeJobStatus.SUCCEEDED
    assert stored.completed_at == T0
    assert first == b"png"
    assert second is None


# Scenario: Duplicate callback
async def test_only_the_first_transition_wins() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        assert await repo.succeed(JobSuccess(job.id, b"one", T0))
        assert not await repo.succeed(JobSuccess(job.id, b"two", T0))
        assert not await repo.fail(JobFailure(job.id, "late", "x", T0))
        assert not await repo.expire(JobDeadline(job.id, T0))
        assert await repo.take_image(job.id) == b"one"


async def test_succeed_refuses_an_overdue_job() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        assert not await repo.succeed(JobSuccess(job.id, b"x", job.expires_at))
        stored = await repo.get(job.id)
    assert stored is not None
    assert stored.status is ImageBridgeJobStatus.PENDING


async def test_fail_records_code_and_bounded_message() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        assert await repo.fail(JobFailure(job.id, "content_policy", "m" * 5000, T0))
        stored = await repo.get(job.id)
    assert stored is not None
    assert stored.status is ImageBridgeJobStatus.FAILED
    assert stored.error_code == "content_policy"
    assert stored.error_message is not None
    assert len(stored.error_message) == 2000


# Scenario: Grok Bot never answers
async def test_expire_marks_a_pending_job() -> None:
    job = pending_job()
    async with sqlite_repository() as repo:
        await repo.create(job)
        assert await repo.expire(JobDeadline(job.id, job.expires_at))
        stored = await repo.get(job.id)
    assert stored is not None
    assert stored.status is ImageBridgeJobStatus.EXPIRED


async def test_sweep_expires_overdue_and_purges_old_rows() -> None:
    fresh = pending_job()
    overdue = replace(pending_job(), expires_at=T0 - timedelta(seconds=1))
    old = replace(pending_job(), created_at=T0 - timedelta(days=8))
    async with sqlite_repository() as repo:
        for job in (fresh, overdue, old):
            await repo.create(job)
        await repo.sweep(T0)
        kept_fresh = await repo.get(fresh.id)
        kept_overdue = await repo.get(overdue.id)
        purged = await repo.get(old.id)
    assert kept_fresh is not None
    assert kept_fresh.status is ImageBridgeJobStatus.PENDING
    assert kept_overdue is not None
    assert kept_overdue.status is ImageBridgeJobStatus.EXPIRED
    assert purged is None
