"""Run one pending Grok cover generation to ``succeeded`` or ``failed``.

The run checks the photos can be read and re-encoded, ends its read
transaction, and hands the job to the bridge, whose body links to them (the
Grok Bot fetches each one with the callback token while the job is pending). Once a bridge slot is free the job's claim records ``started_at``
only if the row is still pending (the stale reaper times started rows from
there); a row failed meanwhile cancels the job before any photo is sent. The
image is then validated and stored as a private ``cover`` creator asset and
the row settled. Every failure settles it ``failed`` with a code and leaves no
asset behind: the stored result is committed by the asset store, so a result
whose settle fails is discarded (row and file) in a fresh transaction.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog

from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationRun,
    CoverGenerationStore,
    CoverResults,
    OwnerPhotos,
    log_generation,
)
from rag_backend.domain.constants.cover_generation import (
    ERROR_DETAIL_LENGTH,
    FAILURE_BRIDGE,
    FAILURE_INVALID_IMAGE,
    FAILURE_NOT_PENDING,
    FAILURE_PHOTO_UNREADABLE,
    FAILURE_UNEXPECTED,
    LOG_COVER_GENERATION_CANCELLED,
    LOG_COVER_GENERATION_CRASHED,
    LOG_COVER_GENERATION_FAILED,
    LOG_COVER_GENERATION_SUCCEEDED,
)
from rag_backend.domain.models.cover_generation import (
    CoverEditJob,
    CoverGeneration,
    CoverGenerationOutcome,
    CoverGenerationStatus,
    CoverJobCancelledError,
)
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.domain.protocols import CoverImageEditor

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, kw_only=True)
class CoverRunDeps:
    """The ports of one background run (its own session)."""

    store: CoverGenerationStore
    photos: OwnerPhotos
    results: CoverResults
    editor: CoverImageEditor
    render_prompt: Callable[[str], str]
    now: Callable[[], datetime]


class CoverGenerationRunner:
    """Run one pending generation to ``succeeded`` or ``failed``."""

    def __init__(self, deps: CoverRunDeps) -> None:
        self._deps = deps

    async def run(self, run: CoverGenerationRun) -> CoverGenerationStatus:
        """Send, store and settle; the final status.

        Any unexpected error (a file gone mid-read, a database error) is rolled
        back and settles the row ``failed`` too, so it never stays pending.
        """
        try:
            return await self._attempt(run)
        except Exception:
            logger.exception(
                LOG_COVER_GENERATION_CRASHED, generation_id=str(run.generation.id)
            )
            await self._deps.store.rollback()
            return await self._fail(run.generation, FAILURE_UNEXPECTED)

    def _claim(self, generation: CoverGeneration) -> Callable[[], Awaitable[bool]]:
        async def claim() -> bool:
            started = await self._deps.store.mark_started(
                generation.id, self._deps.now()
            )
            await self._deps.store.commit()
            return started

        return claim

    async def _attempt(self, run: CoverGenerationRun) -> CoverGenerationStatus:
        generation = run.generation
        try:
            photos = await self._deps.photos.load(run.photo_ids)
        except CoverAssetError:
            return await self._fail(generation, FAILURE_PHOTO_UNREADABLE)
        await self._deps.store.rollback()
        job = CoverEditJob(
            job_id=generation.id,
            prompt=self._deps.render_prompt(run.prompt),
            photo_count=len(photos),
            project_id=generation.project_id,
            claim=self._claim(generation),
        )
        try:
            image = await self._deps.editor.edit_image(job)
        except CoverJobCancelledError:
            log_generation(generation, LOG_COVER_GENERATION_CANCELLED)
            return CoverGenerationStatus.FAILED
        except RuntimeError as exc:
            return await self._fail(generation, FAILURE_BRIDGE, str(exc))
        try:
            asset_id = await self._deps.results.store(generation.owner_id, image)
        except CoverAssetError:
            return await self._fail(generation, FAILURE_INVALID_IMAGE)
        return await self._succeed(generation, asset_id)

    async def _succeed(
        self, generation: CoverGeneration, asset_id: UUID
    ) -> CoverGenerationStatus:
        outcome = CoverGenerationOutcome(
            generation_id=generation.id, at=self._deps.now(), result_asset_id=asset_id
        )
        try:
            settled = await self._deps.store.settle(outcome)
        except Exception:
            await self._deps.store.rollback()
            await self._deps.results.discard(asset_id)
            await self._deps.store.commit()
            raise
        if not settled:
            await self._deps.results.discard(asset_id)
            await self._deps.store.commit()
            log_generation(
                generation, LOG_COVER_GENERATION_FAILED, error_code=FAILURE_NOT_PENDING
            )
            return CoverGenerationStatus.FAILED
        await self._deps.store.commit()
        log_generation(
            generation, LOG_COVER_GENERATION_SUCCEEDED, asset_id=str(asset_id)
        )
        return CoverGenerationStatus.SUCCEEDED

    async def _fail(
        self, generation: CoverGeneration, code: str, detail: str = ""
    ) -> CoverGenerationStatus:
        """Settle ``failed``; ``detail`` is the Grok Bot's own reason, when any."""
        reason = detail[:ERROR_DETAIL_LENGTH] or None
        outcome = CoverGenerationOutcome(
            generation_id=generation.id,
            at=self._deps.now(),
            error_code=code,
            error_detail=reason,
        )
        await self._deps.store.settle(outcome)
        await self._deps.store.commit()
        log_generation(
            generation, LOG_COVER_GENERATION_FAILED, error_code=code, reason=reason
        )
        return CoverGenerationStatus.FAILED


__all__ = ["CoverGenerationRunner", "CoverRunDeps"]
