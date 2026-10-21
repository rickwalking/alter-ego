"""Cover + one image per section for a generated post (ADR-0025).

Built on the editor's :class:`BlogImageService`: one image template,
one blog-images store, one serving route. This module adds what bulk
generation needs on top of it:

* bounded concurrency (``BLOG_IMAGE_CONCURRENCY``), cover first;
* the per-post image cap (the ``BLOG_IMAGE_COST_CAP`` counter): the
  caller passes how many images the post may still generate, and only that
  many slots are attempted;
* best-effort slots: a failed or capped slot stays ``null`` with an error that
  names it; nothing here ever fails the draft;
* a budget sized by the slot count: ``wave_seconds`` per wave of
  ``concurrency`` images. When it runs out, the images that finished are kept
  and every unfinished slot gets ``image_timeout`` (the retry fills it).
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass

import structlog

from rag_backend.application.services.blog.blog_image_service import (
    BlogImageError,
    BlogImageRequest,
    BlogImageService,
    default_scene,
)
from rag_backend.application.services.blog.blog_image_store import BlogImageStore
from rag_backend.application.services.blog_workflow_observability import (
    BlogPhaseScope,
    blog_phase_trace,
)
from rag_backend.domain.constants.blog_editor import PHASE_BLOG_SECTION_IMAGE
from rag_backend.domain.constants.blog_generation import (
    AGENT_BLOG_IMAGES,
    ERR_IMAGE_COST_CAP,
    ERR_IMAGE_TIMEOUT,
    ERROR_KEY_CODE,
    ERROR_KEY_REASON,
    ERROR_KEY_SLOT,
    LOG_IMAGE_FAILED,
    LOG_IMAGES_DONE,
    LOG_IMAGES_TIMED_OUT,
    TRACE_INPUT_POST_ID,
    TRACE_INPUT_SECTION_HEADING,
    TRACE_INPUT_SLOT,
    TRACE_OUTPUT_IMAGE_URL,
)
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_OUTPUT_STATUS_COMPLETED,
    TRACE_STATUS_FIELD,
)
from rag_backend.domain.models.blog_document import BlogImage
from rag_backend.domain.models.blog_generation import GenerationTrace, ImageSubject

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BlogImageBatchDeps:
    """The single-image service + store and the batch concurrency."""

    images: BlogImageService
    store: BlogImageStore
    concurrency: int


@dataclass(frozen=True)
class ImageBatchRequest:
    """The slots to fill, in order (cover first), how many images the post
    may still generate and the budget of one wave (``None`` = unbounded)."""

    trace: GenerationTrace
    subjects: tuple[ImageSubject, ...]
    max_images: int
    wave_seconds: float | None = None


@dataclass(frozen=True)
class ImageBatchResult:
    """Stored images by slot and one error per empty slot."""

    images: dict[str, BlogImage]
    errors: tuple[dict[str, object], ...]


def _slot_error(slot: str, code: str, reason: str) -> dict[str, object]:
    return {ERROR_KEY_SLOT: slot, ERROR_KEY_CODE: code, ERROR_KEY_REASON: reason}


@dataclass(frozen=True)
class _SlotOutcome:
    slot: str
    image: BlogImage | None
    error: dict[str, object] | None


class BlogImageBatchService:
    """Generates the empty image slots of one post (best-effort)."""

    def __init__(self, deps: BlogImageBatchDeps) -> None:
        self._deps = deps

    async def generate(self, request: ImageBatchRequest) -> ImageBatchResult:
        """Cover first, bounded concurrency, budget-capped; never raises per slot."""
        allowed = max(0, request.max_images)
        attempted = request.subjects[:allowed]
        finished = await self._run_within_budget(request, attempted)
        images = {o.slot: o.image for o in finished.values() if o.image is not None}
        errors = [o.error for o in finished.values() if o.error is not None]
        errors.extend(
            _slot_error(subject.slot, ERR_IMAGE_TIMEOUT, ERR_IMAGE_TIMEOUT)
            for subject in attempted
            if subject.slot not in finished
        )
        errors.extend(
            _slot_error(subject.slot, ERR_IMAGE_COST_CAP, ERR_IMAGE_COST_CAP)
            for subject in request.subjects[allowed:]
        )
        logger.info(
            LOG_IMAGES_DONE,
            post_id=request.trace.post_id,
            image_count=len(images),
            attempted=len(attempted),
            slots=len(request.subjects),
            failed=len(errors),
        )
        return ImageBatchResult(images=images, errors=tuple(errors))

    def budget_seconds(self, request: ImageBatchRequest, slots: int) -> float | None:
        """``wave_seconds`` x ceil(slots / concurrency); ``None`` = unbounded."""
        if request.wave_seconds is None:
            return None
        waves = math.ceil(slots / self._concurrency())
        return request.wave_seconds * max(1, waves)

    async def _run_within_budget(
        self, request: ImageBatchRequest, attempted: tuple[ImageSubject, ...]
    ) -> dict[str, _SlotOutcome]:
        """Every slot's outcome as it finishes; unfinished slots are absent."""
        finished: dict[str, _SlotOutcome] = {}
        gate = asyncio.Semaphore(self._concurrency())

        async def one(subject: ImageSubject) -> None:
            outcome = await self._bounded(gate, (request.trace, subject))
            finished[subject.slot] = outcome

        try:
            async with asyncio.timeout(self.budget_seconds(request, len(attempted))):
                await asyncio.gather(*(one(subject) for subject in attempted))
        except TimeoutError:
            logger.warning(
                LOG_IMAGES_TIMED_OUT,
                post_id=request.trace.post_id,
                finished=len(finished),
                attempted=len(attempted),
            )
        return finished

    def _concurrency(self) -> int:
        return max(1, self._deps.concurrency)

    def discard(self, post_id: str, images: dict[str, BlogImage]) -> None:
        """Delete the stored files of ``images`` (their write failed)."""
        for image in images.values():
            self._deps.store.delete(post_id, image.url.rsplit("/", 1)[-1])

    async def _bounded(
        self, gate: asyncio.Semaphore, job: tuple[GenerationTrace, ImageSubject]
    ) -> _SlotOutcome:
        async with gate:
            return await self._one(*job)

    async def _one(self, trace: GenerationTrace, subject: ImageSubject) -> _SlotOutcome:
        scope = BlogPhaseScope(
            project_id=trace.project_id,
            user_id=trace.user_id,
            phase=PHASE_BLOG_SECTION_IMAGE,
            agent_name=AGENT_BLOG_IMAGES,
        )
        request = BlogImageRequest(
            post_id=trace.post_id,
            scene=default_scene(subject.heading, subject.body),
            alt=subject.heading,
        )
        trace_input = {
            TRACE_INPUT_POST_ID: trace.post_id,
            TRACE_INPUT_SLOT: subject.slot,
            TRACE_INPUT_SECTION_HEADING: subject.heading,
        }
        try:
            with blog_phase_trace(scope, trace_input=trace_input) as trace_handle:
                image = await self._deps.images.generate(request)
                trace_handle.set_output({
                    TRACE_STATUS_FIELD: TRACE_OUTPUT_STATUS_COMPLETED,
                    TRACE_INPUT_SLOT: subject.slot,
                    TRACE_OUTPUT_IMAGE_URL: image.url,
                })
        except BlogImageError as exc:
            logger.warning(LOG_IMAGE_FAILED, slot=subject.slot, code=exc.code)
            return _SlotOutcome(
                subject.slot, None, _slot_error(subject.slot, exc.code, exc.code)
            )
        return _SlotOutcome(subject.slot, image, None)


__all__ = [
    "BlogImageBatchDeps",
    "BlogImageBatchService",
    "ImageBatchRequest",
    "ImageBatchResult",
]
