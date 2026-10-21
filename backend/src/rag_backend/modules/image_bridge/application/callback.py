"""Record a Grok Bot callback on its job (contract section 2.2).

The route authenticates first (``authorize``), then hands the raw body to
``record``. Transitions are conditional on the job still being pending, so
a duplicate or late callback never writes twice.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

import structlog

from rag_backend.modules.image_bridge.constants import (
    ERROR_CODE_INVALID_IMAGE,
    ERROR_CODE_MALFORMED,
    LOG_CALLBACK_RECORDED,
)
from rag_backend.modules.image_bridge.domain.callback_body import (
    CallbackError,
    CallbackImage,
    decode_image_b64,
    parse_callback,
)
from rag_backend.modules.image_bridge.domain.exceptions import (
    InvalidCallbackImageError,
)
from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    ImageBridgeJobStatus,
    JobDeadline,
    JobFailure,
    JobSuccess,
)
from rag_backend.modules.image_bridge.domain.ports import (
    BridgeClock,
    ImageBridgeJobRepository,
    ImageCodec,
)
from rag_backend.modules.image_bridge.domain.tokens import token_matches

logger = structlog.get_logger()


class CallbackOutcome(StrEnum):
    """What the route answers: 202, 409 or 422."""

    ACCEPTED = "accepted"
    NOT_PENDING = "not_pending"
    INVALID = "invalid"


@dataclass(frozen=True)
class CallbackDeps:
    """Ports the callback use case needs."""

    repository: ImageBridgeJobRepository
    codec: ImageCodec
    clock: BridgeClock


@dataclass(frozen=True)
class CallbackAuth:
    """The job id from the path and the token from the header."""

    job_id: str
    token: str | None


class ImageBridgeCallbackService:
    """Authenticates and records Grok Bot callbacks."""

    def __init__(self, deps: CallbackDeps) -> None:
        self._deps = deps

    async def authorize(self, auth: CallbackAuth) -> ImageBridgeJob | None:
        """The job when the token matches; ``None`` for a bad token or job."""
        job = await self._find(auth.job_id)
        digest = job.token_sha256 if job is not None else None
        if not token_matches(auth.token, digest):
            return None
        return job

    async def record(self, job: ImageBridgeJob, body: bytes) -> CallbackOutcome:
        """Validate the body and store the image or the error on the job.

        ``MalformedCallbackError``, JSON and UTF-8 errors are all
        ``ValueError``.
        """
        now = self._deps.clock.now()
        if job.status is not ImageBridgeJobStatus.PENDING:
            return CallbackOutcome.NOT_PENDING
        if job.is_overdue(now):
            await self._deps.repository.expire(JobDeadline(job_id=job.id, at=now))
            return CallbackOutcome.NOT_PENDING
        try:
            parsed = parse_callback(json.loads(body))
        except (ValueError, RecursionError) as exc:
            failure = JobFailure(job.id, ERROR_CODE_MALFORMED, str(exc), now)
            return await self._fail(failure, CallbackOutcome.INVALID)
        if isinstance(parsed, CallbackError):
            failure = JobFailure(job.id, parsed.code, parsed.message, now)
            return await self._fail(failure, CallbackOutcome.ACCEPTED)
        return await self._store_image(job, parsed)

    async def _store_image(
        self, job: ImageBridgeJob, parsed: CallbackImage
    ) -> CallbackOutcome:
        now = self._deps.clock.now()
        try:
            image = decode_image_b64(parsed.b64_json)
            await asyncio.to_thread(self._deps.codec.validate, image)
        except InvalidCallbackImageError as exc:
            failure = JobFailure(job.id, ERROR_CODE_INVALID_IMAGE, str(exc), now)
            return await self._fail(failure, CallbackOutcome.INVALID)
        stored = await self._deps.repository.succeed(JobSuccess(job.id, image, now))
        logger.info(LOG_CALLBACK_RECORDED, bridge_job_id=str(job.id), stored=stored)
        return CallbackOutcome.ACCEPTED if stored else CallbackOutcome.NOT_PENDING

    async def _fail(
        self, failure: JobFailure, outcome: CallbackOutcome
    ) -> CallbackOutcome:
        stored = await self._deps.repository.fail(failure)
        logger.info(
            LOG_CALLBACK_RECORDED,
            bridge_job_id=str(failure.job_id),
            error_code=failure.code,
            stored=stored,
        )
        return outcome if stored else CallbackOutcome.NOT_PENDING

    async def _find(self, raw_id: str) -> ImageBridgeJob | None:
        try:
            job_id = UUID(raw_id)
        except ValueError:
            return None
        return await self._deps.repository.get(job_id)
