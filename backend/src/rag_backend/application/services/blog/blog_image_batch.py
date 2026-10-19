"""Cover + one image per section for a generated post (AE-0425, ADR-0025).

Built on the editor's :class:`BlogImageService` (AE-0424): one image template,
one blog-images store, one serving route. This module adds what bulk
generation needs on top of it:

* bounded concurrency (``BLOG_IMAGE_CONCURRENCY``), cover first;
* the per-post spend cap: the caller passes the budget still available for
  this post (``BLOG_IMAGE_COST_CAP`` minus what earlier attempts spent), and
  only that many slots are attempted;
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
from rag_backend.application.services.blog_workflow_observability import (
    BlogPhaseScope,
    blog_phase_trace,
)
from rag_backend.domain.constants.blog_editor import PHASE_BLOG_SECTION_IMAGE
from rag_backend.domain.constants.blog_generation import (
    AGENT_BLOG_IMAGES,
    BLOG_IMAGE_ESTIMATED_COST_USD,
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

_COST_EPSILON = 1e-9


@dataclass(frozen=True)
class BlogImageBatchDeps:
    """The single-image service (AE-0424) and the batch concurrency."""

    images: BlogImageService
    concurrency: int


@dataclass(frozen=True)
class ImageBatchRequest:
    """The slots to fill, in order (cover first), and the budget left (USD)."""

    trace: GenerationTrace
    subjects: tuple[ImageSubject, ...]
    budget_usd: float


@dataclass(frozen=True)
class ImageBatchResult:
    """Stored images by slot, one error per empty slot, and what was spent."""

    images: dict[str, BlogImage]
    errors: tuple[dict[str, object], ...]
    spent_usd: float


def image_budget(budget_usd: float) -> int:
    """How many images ``budget_usd`` pays for."""
    if budget_usd <= 0:
        return 0
    return int((budget_usd + _COST_EPSILON) // BLOG_IMAGE_ESTIMATED_COST_USD)


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
        allowed = image_budget(request.budget_usd)
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
        spent = len(attempted) * BLOG_IMAGE_ESTIMATED_COST_USD
        logger.info(
            LOG_IMAGES_DONE,
            post_id=request.trace.post_id,
            image_count=len(images),
            slots=len(request.subjects),
            failed=len(errors),
            estimated_cost_usd=spent,
        )
        return ImageBatchResult(images=images, errors=tuple(errors), spent_usd=spent)

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
    "image_budget",
]
