"""``GrokBotImageService``: job, webhook, wait, normalize.

Gherkin: tests/features/image_bridge.feature
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image

from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    carousel_run_epoch_var,
)
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    ImageBridgeJobError,
    WebhookDeliveryError,
)
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    JobDeadline,
    JobFailure,
    JobSuccess,
    WebhookRequest,
)
from rag_backend.modules.image_bridge.domain.tokens import token_digest
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.unit.modules.image_bridge.support import (
    FakeClock,
    FakeWebhook,
    png_bytes,
    sqlite_repository,
)

BASE_URL = "https://marinssolutions.com/"


def _service(
    repo: SqlImageBridgeJobRepository,
    probe: tuple[FakeWebhook, FakeClock],
    max_concurrency: int = 2,
) -> GrokBotImageService:
    webhook, clock = probe
    deps = GrokBotImageDeps(
        repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
    )
    config = GrokBotImageConfig(
        callback_base_url=BASE_URL, max_concurrency=max_concurrency
    )
    return GrokBotImageService(deps, config)


def _answer_each_job(
    repo: SqlImageBridgeJobRepository, webhook: FakeWebhook, clock: FakeClock
):
    """``on_sleep`` hook: the 'other worker' records an image per delivered job."""
    answered: set[UUID] = set()

    async def answer() -> None:
        for request in webhook.requests:
            if request.job_id in answered:
                continue
            answered.add(request.job_id)
            await repo.succeed(
                JobSuccess(request.job_id, png_bytes((1122, 1402)), clock.now())
            )

    return answer


# Scenario: Grok Bot returns an image
async def test_happy_path_writes_the_image_at_the_requested_size(
    tmp_path: Path,
) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    output = tmp_path / "slides" / "slide_1.jpg"
    async with sqlite_repository() as repo:
        clock.on_sleep = _answer_each_job(repo, webhook, clock)
        service = _service(repo, (webhook, clock))
        token = carousel_run_epoch_var.set(CarouselRunContext("proj-1", 3))
        try:
            result = await service.generate_image("a neon slide", str(output))
        finally:
            carousel_run_epoch_var.reset(token)
        request = webhook.requests[0]
        job = await repo.get(request.job_id)
        leftover = await repo.take_image(request.job_id)

    assert result == str(output)
    with Image.open(output) as img:
        assert img.format == "PNG"
        assert img.size == (1536, 1024)
    assert request.prompt == "a neon slide"
    assert request.size == "1536x1024"
    assert request.model == "gpt-image-2"
    assert request.callback_url == (
        f"https://marinssolutions.com/api/v1/image-bridge/jobs/{request.job_id}/result"
    )
    assert len(request.callback_token) == 43
    assert request.metadata == {"content_type": "carousel", "project_id": "proj-1"}
    assert job is not None
    assert job.status is ImageBridgeJobStatus.SUCCEEDED
    # Scenario: Tokens are never stored or logged in clear
    assert job.token_sha256 == token_digest(request.callback_token)
    assert job.token_sha256 != request.callback_token
    # Scenario: The waiter works across processes (bytes nulled after the read)
    assert leftover is None
    assert clock.sleeps == [2.0]


# Scenario: Webhook is down
async def test_webhook_failure_fails_the_job_at_once(tmp_path: Path) -> None:
    webhook = FakeWebhook(
        error=WebhookDeliveryError("Grok Bot webhook answered HTTP 500")
    )
    clock = FakeClock()
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))
        job = await repo.get(webhook.requests[0].job_id)
    assert job is not None
    assert job.status is ImageBridgeJobStatus.FAILED
    assert job.error_code == "webhook_failed"
    assert clock.sleeps == []


# Scenario: Grok Bot refuses
async def test_error_callback_raises_with_the_code(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:

        async def refuse() -> None:
            job_id = webhook.requests[0].job_id
            await repo.fail(JobFailure(job_id, "content_policy", "no", clock.now()))

        clock.on_sleep = refuse
        service = _service(repo, (webhook, clock))
        with pytest.raises(ImageBridgeJobError, match="content_policy"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))
    assert not (tmp_path / "x.jpg").exists()


# Scenario: Grok Bot never answers
async def test_timeout_expires_the_job(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))
        with pytest.raises(ImageBridgeJobError, match="expired after 600s"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))
        job = await repo.get(webhook.requests[0].job_id)
    assert job is not None
    assert job.status is ImageBridgeJobStatus.EXPIRED
    assert len(clock.sleeps) == 300


async def test_job_expired_by_another_worker_raises(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:

        async def sweep_elsewhere() -> None:
            job_id = webhook.requests[0].job_id
            await repo.expire(JobDeadline(job_id, clock.now()))

        clock.on_sleep = sweep_elsewhere
        service = _service(repo, (webhook, clock))
        with pytest.raises(ImageBridgeJobError, match="expired"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))


@dataclass
class _DelegatingRepository:
    """Forwards every port call to the SQLite repository."""

    inner: SqlImageBridgeJobRepository
    clock: FakeClock

    async def create(self, job: ImageBridgeJob) -> None:
        await self.inner.create(job)

    async def get(self, job_id: UUID) -> ImageBridgeJob | None:
        return await self.inner.get(job_id)

    async def succeed(self, success: JobSuccess) -> bool:
        return await self.inner.succeed(success)

    async def fail(self, failure: JobFailure) -> bool:
        return await self.inner.fail(failure)

    async def expire(self, deadline: JobDeadline) -> bool:
        return await self.inner.expire(deadline)

    async def take_image(self, job_id: UUID) -> bytes | None:
        return await self.inner.take_image(job_id)

    async def sweep(self, now: datetime) -> None:
        await self.inner.sweep(now)


@dataclass
class _RacingRepository(_DelegatingRepository):
    """Lets the callback land between the overdue read and the expire."""

    expired_calls: list[UUID] = field(default_factory=list)

    async def expire(self, deadline: JobDeadline) -> bool:
        """Simulates the other worker recording the image just before the deadline."""
        self.expired_calls.append(deadline.job_id)
        before_deadline = self.clock.now().replace(year=2000)
        await self.inner.succeed(
            JobSuccess(deadline.job_id, png_bytes(), before_deadline)
        )
        return await self.inner.expire(deadline)


@dataclass
class _InFlight:
    current: int = 0
    peak: int = 0


@dataclass
class _CountingWebhook(FakeWebhook):
    in_flight: _InFlight = field(default_factory=_InFlight)

    async def deliver(self, request: WebhookRequest) -> None:
        self.in_flight.current += 1
        self.in_flight.peak = max(self.in_flight.peak, self.in_flight.current)
        await super().deliver(request)


@dataclass
class _CountingRepository(_DelegatingRepository):
    in_flight: _InFlight = field(default_factory=_InFlight)

    async def take_image(self, job_id: UUID) -> bytes | None:
        self.in_flight.current -= 1
        return await self.inner.take_image(job_id)


async def test_callback_winning_the_deadline_race_is_used(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as inner:
        repo = _RacingRepository(inner, clock)
        deps = GrokBotImageDeps(
            repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
        )
        service = GrokBotImageService(
            deps, GrokBotImageConfig(callback_base_url=BASE_URL, timeout_seconds=4)
        )
        await service.generate_image("p", str(tmp_path / "x.jpg"))
    assert len(repo.expired_calls) == 1
    assert (tmp_path / "x.jpg").exists()


@dataclass
class _VanishingRepository(_RacingRepository):
    async def get(self, job_id: UUID) -> ImageBridgeJob | None:
        return None


async def test_vanished_job_raises(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as inner:
        repo = _VanishingRepository(inner, clock)
        deps = GrokBotImageDeps(
            repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
        )
        service = GrokBotImageService(deps, GrokBotImageConfig(BASE_URL))
        with pytest.raises(ImageBridgeJobError, match="disappeared"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))


async def test_succeeded_job_whose_bytes_were_taken_raises(tmp_path: Path) -> None:
    webhook, clock = FakeWebhook(), FakeClock()
    async with sqlite_repository() as repo:

        async def steal() -> None:
            job_id = webhook.requests[0].job_id
            await repo.succeed(JobSuccess(job_id, png_bytes(), clock.now()))
            await repo.take_image(job_id)

        clock.on_sleep = steal
        service = _service(repo, (webhook, clock))
        with pytest.raises(ImageBridgeJobError, match="without image bytes"):
            await service.generate_image("p", str(tmp_path / "x.jpg"))


# Scenario: Concurrency is capped
async def test_three_requests_with_a_cap_of_two(tmp_path: Path) -> None:
    in_flight = _InFlight()
    webhook, clock = _CountingWebhook(in_flight=in_flight), FakeClock()
    async with sqlite_repository() as inner:
        repo = _CountingRepository(inner, clock, in_flight=in_flight)
        answer = _answer_each_job(inner, webhook, clock)

        async def slow_answer() -> None:
            await asyncio.sleep(0.01)
            await answer()

        clock.on_sleep = slow_answer
        deps = GrokBotImageDeps(
            repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
        )
        service = GrokBotImageService(
            deps, GrokBotImageConfig(callback_base_url=BASE_URL, max_concurrency=2)
        )
        paths = [str(tmp_path / f"s{index}.jpg") for index in range(3)]
        results = await asyncio.gather(
            *(service.generate_image("p", path) for path in paths)
        )
    assert results == paths
    assert in_flight.peak == 2
    assert len(webhook.requests) == 3


async def test_invalid_configured_size_fails_fast() -> None:
    async with sqlite_repository() as repo:
        deps = GrokBotImageDeps(
            repository=repo,
            webhook=FakeWebhook(),
            codec=PillowImageCodec(),
            clock=FakeClock(),
        )
        with pytest.raises(ValueError, match="WIDTHxHEIGHT"):
            GrokBotImageService(deps, GrokBotImageConfig(BASE_URL, size="big"))
