"""A re-run image phase waits on the bridge job its dead driver started."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageConfig,
    GrokBotImageDeps,
    GrokBotImageService,
    image_job_id,
)
from rag_backend.modules.image_bridge.domain.models import JobFailure, JobSuccess
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.image_bridge.infrastructure.repository import (
    SqlImageBridgeJobRepository,
)
from tests.unit.modules.image_bridge.support import (
    FakeClock,
    FakeWebhook,
    pending_job,
    png_bytes,
    sqlite_repository,
)

PROMPT = "a neon slide"


def _service(
    repo: SqlImageBridgeJobRepository, webhook: FakeWebhook, clock: FakeClock
) -> GrokBotImageService:
    deps = GrokBotImageDeps(
        repository=repo, webhook=webhook, codec=PillowImageCodec(), clock=clock
    )
    return GrokBotImageService(deps, GrokBotImageConfig(callback_base_url="https://x/"))


def test_the_job_id_follows_the_image_and_prompt() -> None:
    """Scenario: A re-run image waits for the job its dead driver started"""
    assert image_job_id("a.jpg", PROMPT) == image_job_id("a.jpg", PROMPT)
    assert image_job_id("a.jpg", PROMPT) != image_job_id("b.jpg", PROMPT)
    assert image_job_id("a.jpg", PROMPT) != image_job_id("a.jpg", "other")


async def test_a_pending_job_is_awaited_not_sent_again(tmp_path: Path) -> None:
    """Scenario: A re-run image waits for the job its dead driver started"""
    output = tmp_path / "slide_1.jpg"
    webhook, clock = FakeWebhook(), FakeClock()
    job_id = image_job_id(str(output), PROMPT)
    async with sqlite_repository() as repo:
        await repo.create(replace(pending_job(clock.now()), id=job_id))

        async def callback_arrives() -> None:
            await repo.succeed(JobSuccess(job_id, png_bytes(), clock.now()))

        clock.on_sleep = callback_arrives
        await _service(repo, webhook, clock).generate_image(PROMPT, str(output))
    assert webhook.requests == []
    assert output.exists()


async def test_a_failed_job_is_replaced_by_a_new_one(tmp_path: Path) -> None:
    """Scenario: A re-run image waits for the job its dead driver started"""
    output = tmp_path / "slide_2.jpg"
    webhook, clock = FakeWebhook(), FakeClock()
    job_id = image_job_id(str(output), PROMPT)
    async with sqlite_repository() as repo:
        await repo.create(replace(pending_job(clock.now()), id=job_id))
        await repo.fail(JobFailure(job_id, "generation_error", "boom", clock.now()))

        async def callback_arrives() -> None:
            for request in webhook.requests:
                await repo.succeed(
                    JobSuccess(request.job_id, png_bytes(), clock.now())
                )

        clock.on_sleep = callback_arrives
        await _service(repo, webhook, clock).generate_image(PROMPT, str(output))
    assert len(webhook.requests) == 1
    assert webhook.requests[0].job_id != job_id
