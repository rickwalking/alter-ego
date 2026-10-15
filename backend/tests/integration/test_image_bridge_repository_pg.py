"""Image bridge job store on real Postgres (AE-0393, AC6/AC11).

Gherkin: tests/features/image_bridge.feature
  Scenario: The waiter works across processes
  Scenario: Duplicate callback
  Scenario: Grok Bot never answers

Two engines on one isolated schema stand in for two uvicorn workers: one
records the callback, the other polls and reads the bytes. Skipped unless
``DATABASE_URL`` points at Postgres.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rag_backend.modules.image_bridge.application.callback import (
    CallbackAuth,
    CallbackDeps,
    CallbackOutcome,
    ImageBridgeCallbackService,
)
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
)
from rag_backend.modules.image_bridge.constants import TABLE_IMAGE_BRIDGE_JOBS
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJobStatus,
    JobDeadline,
    JobFailure,
    JobSuccess,
)
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.unit.modules.image_bridge.support import (
    T0,
    FakeClock,
    FakeWebhook,
    images_response,
    pending_job,
    png_bytes,
)

pytestmark = [pytest.mark.integration, requires_postgres]

_TABLES = (TABLE_IMAGE_BRIDGE_JOBS,)


def _repository(engine: AsyncEngine) -> SqlImageBridgeJobRepository:
    maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )
    return SqlImageBridgeJobRepository(lambda: maker)


async def _second_worker(engine: AsyncEngine) -> AsyncEngine:
    """Another engine on the same schema: a separate connection pool."""
    async with engine.connect() as conn:
        search_path = await conn.scalar(text("SHOW search_path"))
    return create_async_engine(
        os.environ["DATABASE_URL"],
        connect_args={"server_settings": {"search_path": str(search_path)}},
    )


# Scenario: The waiter works across processes (bytea round trip, nulled)
async def test_bytes_round_trip_through_bytea_and_are_nulled() -> None:
    image = png_bytes((1122, 1402))
    job = pending_job()
    async with isolated_schema(_TABLES) as engine:
        repo = _repository(engine)
        await repo.create(job)
        assert await repo.succeed(JobSuccess(job.id, image, T0))
        first = await repo.take_image(job.id)
        second = await repo.take_image(job.id)
        async with engine.connect() as conn:
            stored = await conn.scalar(
                text("SELECT image_bytes FROM image_bridge_jobs WHERE id = :id"),
                {"id": job.id},
            )
    assert first == image
    assert second is None
    assert stored is None


# Scenario: The waiter works across processes (poll + callback on two workers)
async def test_waiter_reads_a_callback_recorded_by_another_worker(
    tmp_path: Path,
) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with isolated_schema(_TABLES) as engine:
        other = await _second_worker(engine)
        try:
            callback = ImageBridgeCallbackService(
                CallbackDeps(
                    repository=_repository(other),
                    codec=PillowImageCodec(),
                    clock=clock,
                )
            )

            async def other_worker_receives_the_callback() -> None:
                request = webhook.requests[0]
                job = await callback.authorize(
                    CallbackAuth(str(request.job_id), request.callback_token)
                )
                assert job is not None
                body = images_response(png_bytes((1122, 1402)))
                outcome = await callback.record(job, json.dumps(body).encode())
                assert outcome is CallbackOutcome.ACCEPTED

            clock.on_sleep = other_worker_receives_the_callback
            waiter = GrokBotImageService(
                GrokBotImageDeps(
                    repository=_repository(engine),
                    webhook=webhook,
                    codec=PillowImageCodec(),
                    clock=clock,
                ),
                GrokBotImageConfig(callback_base_url="https://marinssolutions.com"),
            )
            output = tmp_path / "slide.jpg"
            await waiter.generate_image("slide", str(output))
        finally:
            await other.dispose()
    with Image.open(io.BytesIO(output.read_bytes())) as img:
        assert img.size == (1536, 1024)


# Scenario: Duplicate callback (concurrent writers, one winner)
async def test_concurrent_transitions_have_one_winner() -> None:
    job = pending_job()
    async with isolated_schema(_TABLES) as engine:
        repo = _repository(engine)
        await repo.create(job)
        results = await asyncio.gather(
            repo.succeed(JobSuccess(job.id, b"a", T0)),
            repo.succeed(JobSuccess(job.id, b"b", T0)),
            repo.fail(JobFailure(job.id, "x", "y", T0)),
            repo.expire(JobDeadline(job.id, T0)),
        )
    assert results.count(True) == 1


# Scenario: Grok Bot never answers (expiry + retention sweep)
async def test_expiry_and_sweep_on_postgres() -> None:
    fresh = pending_job()
    overdue = replace(pending_job(), expires_at=T0 - timedelta(seconds=1))
    old = replace(pending_job(), created_at=T0 - timedelta(days=8))
    async with isolated_schema(_TABLES) as engine:
        repo = _repository(engine)
        for job in (fresh, overdue, old):
            await repo.create(job)
        assert not await repo.succeed(JobSuccess(overdue.id, b"late", T0))
        await repo.sweep(T0)
        kept_fresh = await repo.get(fresh.id)
        expired = await repo.get(overdue.id)
        purged = await repo.get(old.id)
    assert kept_fresh is not None
    assert kept_fresh.status is ImageBridgeJobStatus.PENDING
    assert expired is not None
    assert expired.status is ImageBridgeJobStatus.EXPIRED
    assert expired.created_at.tzinfo is not None
    assert purged is None
