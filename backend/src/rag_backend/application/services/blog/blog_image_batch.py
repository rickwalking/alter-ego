"""Cover + one image per section for a generated post (AE-0425, ADR-0025).

Built on the editor's :class:`BlogImageService` (AE-0424): one image template,
one blog-images store, one serving route. This module adds what bulk
generation needs on top of it:

* bounded concurrency (``BLOG_IMAGE_CONCURRENCY``), cover first;
* the per-post image cap (AE-0424's ``BLOG_IMAGE_COST_CAP`` counter): the
  caller passes how many images the post may still generate, and only that
  many slots are attempted;
* best-effort slots: a failed or capped slot stays ``null`` with an error that
  names it; nothing here ever fails the draft.
"""

from __future__ import annotations

import asyncio
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
    ERROR_KEY_CODE,
    ERROR_KEY_REASON,
    ERROR_KEY_SLOT,
    LOG_IMAGE_FAILED,
    LOG_IMAGES_DONE,
)
from rag_backend.domain.models.blog_document import BlogImage
from rag_backend.domain.models.blog_generation import GenerationTrace, ImageSubject

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BlogImageBatchDeps:
    """The single-image service + store (AE-0424) and the batch concurrency."""

    images: BlogImageService
    store: BlogImageStore
    concurrency: int


@dataclass(frozen=True)
class ImageBatchRequest:
    """The slots to fill, in order (cover first), and how many images the
    post may still generate."""

    trace: GenerationTrace
    subjects: tuple[ImageSubject, ...]
    max_images: int


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
        gate = asyncio.Semaphore(max(1, self._deps.concurrency))
        outcomes = await asyncio.gather(
            *(self._bounded(gate, (request.trace, subject)) for subject in attempted)
        )
        images = {o.slot: o.image for o in outcomes if o.image is not None}
        errors = [o.error for o in outcomes if o.error is not None]
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
        try:
            with blog_phase_trace(scope):
                image = await self._deps.images.generate(request)
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
