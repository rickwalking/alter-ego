"""``ImageGenerationService`` backed by the Grok Bot webhook (AE-0393).

One call: create a pending job, POST the webhook, poll Postgres until the
callback lands (any worker may receive it), then write the image fitted to
the configured size as PNG. Every failure raises ``ImageBridgeJobError``, a
``RuntimeError``, the same contract as ``OpenAIImageService``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from rag_backend.domain.models.carousel_run import current_run_context
from rag_backend.domain.protocols import ImageGenerationService
from rag_backend.modules.image_bridge.constants import (
    CALLBACK_URL_TEMPLATE,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_TIMEOUT_SECONDS,
    ERR_JOB_EXPIRED,
    ERR_JOB_FAILED,
    ERR_JOB_MISSING,
    ERR_JOB_NO_IMAGE,
    ERROR_CODE_WEBHOOK_FAILED,
    LOG_JOB_STARTED,
    LOG_JOB_SUCCEEDED,
    LOG_WEBHOOK_FAILED,
    POLL_INTERVAL_SECONDS,
    URL_TRAILING_SLASH,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    ImageBridgeJobError,
    WebhookDeliveryError,
)
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    ImageSize,
    JobDeadline,
    JobFailure,
    WebhookRequest,
    job_metadata,
)
from rag_backend.modules.image_bridge.domain.ports import (
    BridgeClock,
    GrokBotWebhook,
    ImageBridgeJobRepository,
    ImageCodec,
    NormalizeRequest,
)
from rag_backend.modules.image_bridge.domain.tokens import (
    new_callback_token,
    token_digest,
)

logger = structlog.get_logger()


@dataclass(frozen=True)
class GrokBotImageConfig:
    """Tunables of the waiter. ``callback_base_url`` is the public origin."""

    callback_base_url: str
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS
    size: str = DEFAULT_IMAGE_SIZE
    model: str = DEFAULT_IMAGE_MODEL


@dataclass(frozen=True)
class GrokBotImageDeps:
    """Ports the waiter needs."""

    repository: ImageBridgeJobRepository
    webhook: GrokBotWebhook
    codec: ImageCodec
    clock: BridgeClock


@dataclass(frozen=True)
class _StartedJob:
    job: ImageBridgeJob
    token: str


class GrokBotImageService(ImageGenerationService):
    """Generates one image per call through an async Grok Bot job."""

    def __init__(self, deps: GrokBotImageDeps, config: GrokBotImageConfig) -> None:
        self._deps = deps
        self._config = config
        self._size = ImageSize.parse(config.size)
        self._slots = asyncio.Semaphore(config.max_concurrency)

    async def generate_image(self, prompt: str, output_path: str) -> str:
        """Run one bridge job and write its normalized image to ``output_path``."""
        async with self._slots:
            job = await self._start(prompt)
            image = await self._wait(job)
        request = NormalizeRequest(image, self._size.width, self._size.height)
        png = await asyncio.to_thread(self._deps.codec.normalize, request)
        await asyncio.to_thread(_write_file, output_path, png)
        return output_path

    async def _start(self, prompt: str) -> ImageBridgeJob:
        now = self._deps.clock.now()
        await self._deps.repository.sweep(now)
        started = self._new_job()
        await self._deps.repository.create(started.job)
        try:
            await self._deps.webhook.deliver(self._webhook_request(started, prompt))
        except WebhookDeliveryError as exc:
            await self._fail_delivery(started.job, exc)
            raise ImageBridgeJobError(str(exc)) from exc
        logger.info(LOG_JOB_STARTED, bridge_job_id=str(started.job.id))
        return started.job

    def _new_job(self) -> _StartedJob:
        now = self._deps.clock.now()
        token = new_callback_token()
        job = ImageBridgeJob(
            id=uuid4(),
            status=ImageBridgeJobStatus.PENDING,
            size=self._config.size,
            token_sha256=token_digest(token),
            created_at=now,
            expires_at=now + timedelta(seconds=self._config.timeout_seconds),
        )
        return _StartedJob(job=job, token=token)

    def _webhook_request(self, started: _StartedJob, prompt: str) -> WebhookRequest:
        run = current_run_context()
        base = self._config.callback_base_url.rstrip(URL_TRAILING_SLASH)
        return WebhookRequest(
            job_id=started.job.id,
            model=self._config.model,
            prompt=prompt,
            size=self._config.size,
            callback_url=CALLBACK_URL_TEMPLATE.format(base=base, job_id=started.job.id),
            callback_token=started.token,
            expires_at=started.job.expires_at,
            metadata=job_metadata(run.project_id if run is not None else None),
        )

    async def _fail_delivery(
        self, job: ImageBridgeJob, exc: WebhookDeliveryError
    ) -> None:
        logger.warning(LOG_WEBHOOK_FAILED, bridge_job_id=str(job.id), reason=str(exc))
        failure = JobFailure(
            job.id, ERROR_CODE_WEBHOOK_FAILED, str(exc), self._deps.clock.now()
        )
        await self._deps.repository.fail(failure)

    async def _wait(self, started: ImageBridgeJob) -> bytes:
        while True:
            job = await self._deps.repository.get(started.id)
            if job is None:
                raise ImageBridgeJobError(ERR_JOB_MISSING.format(job_id=started.id))
            image = await self._settle(job)
            if image is not None:
                elapsed = self._deps.clock.now() - started.created_at
                logger.info(
                    LOG_JOB_SUCCEEDED,
                    bridge_job_id=str(job.id),
                    wait_seconds=round(elapsed.total_seconds(), 1),
                )
                return image
            await self._deps.clock.sleep(self._config.poll_interval_seconds)

    async def _settle(self, job: ImageBridgeJob) -> bytes | None:
        """The image when done; ``None`` to keep polling; raise on failure."""
        if job.status is ImageBridgeJobStatus.SUCCEEDED:
            return await self._take(job.id)
        if job.status is ImageBridgeJobStatus.FAILED:
            raise ImageBridgeJobError(
                ERR_JOB_FAILED.format(job_id=job.id, code=job.error_code)
            )
        if job.status is ImageBridgeJobStatus.EXPIRED:
            raise self._expired(job.id)
        now = self._deps.clock.now()
        if not job.is_overdue(now):
            return None
        if await self._deps.repository.expire(JobDeadline(job_id=job.id, at=now)):
            raise self._expired(job.id)
        # The callback won the race with the deadline: read it next poll.
        return None

    async def _take(self, job_id: UUID) -> bytes:
        image = await self._deps.repository.take_image(job_id)
        if image is None:
            raise ImageBridgeJobError(ERR_JOB_NO_IMAGE.format(job_id=job_id))
        return image

    def _expired(self, job_id: UUID) -> ImageBridgeJobError:
        return ImageBridgeJobError(
            ERR_JOB_EXPIRED.format(job_id=job_id, seconds=self._config.timeout_seconds)
        )


def _write_file(output_path: str, data: bytes) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
