"""The blog generation run: writer → quality gate → images (AE-0425, ADR-0025).

One run = one lease on one draft row. A full run:

1. drafts ONE continuous article (PT + EN) from the brief (``blog_generation``),
2. normalizes it to exactly N sections (N = the carousel slide count),
3. gates each language (voice score + deterministic scan + one rewrite at most),
4. stores the scored, image-less document (lease-fenced; refuses to overwrite
   an owner save),
5. generates the empty image slots (cover + N sections, ``blog_section_image``)
   within what is left of the post's image budget, best-effort,
6. attaches the images by slot id to the row's CURRENT content (an owner edit
   made during the image step is kept; a section deleted meanwhile is skipped)
   and finishes ``complete`` or ``partial``.

An images-only job (a retry of a post whose article exists) skips 1-4. The
whole run is bounded by ``BLOG_GENERATION_TIMEOUT_SECONDS`` and heartbeats
while it works; a heartbeat failure is logged and never ends the run. A
writer/count/document failure finishes ``failed`` without storing anything as
if valid; cancellation finishes ``failed`` + recoverable and re-raises. A lost
lease stops the run silently. The post always stays a draft.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
)
from rag_backend.application.services.blog.blog_generated_document import (
    GeneratedLanguages,
    ImageTitles,
    attach_images,
    build_generated_document,
    missing_image_subjects,
)
from rag_backend.application.services.blog.blog_generation_job import (
    BlogGenerationDeps,
    GenerationJob,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_image_batch import (
    ImageBatchRequest,
    ImageBatchResult,
)
from rag_backend.application.services.blog.blog_quality_gate import GateCommand
from rag_backend.application.services.blog.blog_section_plan import (
    normalize_section_count,
)
from rag_backend.application.services.blog_workflow_observability import (
    BlogPhaseScope,
    blog_phase_trace,
)
from rag_backend.domain.constants.blog_generation import (
    AGENT_BLOG_WRITER,
    ERR_GENERATION_CANCELLED,
    ERR_GENERATION_CONFLICT,
    ERR_GENERATION_FAILED,
    ERR_GENERATION_LLM_FAILED,
    ERR_GENERATION_TIMEOUT,
    ERR_INVALID_GENERATED_DOCUMENT,
    ERR_SECTION_COUNT_MISMATCH,
    ERROR_KEY_CODE,
    ERROR_KEY_REASON,
    GENERATION_STATUS_COMPLETE,
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_PARTIAL,
    LANGUAGE_EN,
    LANGUAGE_PT,
    LOG_GENERATION_FAILED,
    LOG_GENERATION_FINISHED,
    LOG_GENERATION_LEASE_LOST,
    LOG_HEARTBEAT_FAILED,
    PHASE_BLOG_GENERATION,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    BlogImage,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import (
    ContentMerge,
    ContentWrite,
    DraftArticle,
    GenerationConflictError,
    GenerationLease,
    GenerationOutcome,
    LeaseLostError,
    SectionCountMismatchError,
    WriterBrief,
    WriterFailedError,
)

logger = structlog.get_logger(__name__)

# Failures that end the run as ``failed`` + recoverable (the owner retries).
_FAILURE_CODES: dict[type[Exception], str] = {
    WriterFailedError: ERR_GENERATION_LLM_FAILED,
    SectionCountMismatchError: ERR_SECTION_COUNT_MISMATCH,
    InvalidBlogDocumentError: ERR_INVALID_GENERATED_DOCUMENT,
    GenerationConflictError: ERR_GENERATION_CONFLICT,
}


def _failure_code(exc: Exception) -> str:
    return next(code for kind, code in _FAILURE_CODES.items() if isinstance(exc, kind))


def _failure(code: str, reason: str) -> GenerationOutcome:
    return GenerationOutcome(
        status=GENERATION_STATUS_FAILED,
        errors=({ERROR_KEY_CODE: code, ERROR_KEY_REASON: reason},),
        recoverable=True,
    )


class BlogGenerationService:
    """Runs one generation job end to end (see the module docstring)."""

    def __init__(self, deps: BlogGenerationDeps) -> None:
        self._deps = deps

    async def run(self, job: GenerationJob) -> GenerationOutcome | None:
        """Run the job; the recorded outcome (``None`` if the lease was lost)."""
        try:
            async with asyncio.timeout(self._deps.timings.timeout_seconds):
                outcome = await self._with_heartbeat(job)
        except TimeoutError:
            outcome = _failure(ERR_GENERATION_TIMEOUT, ERR_GENERATION_TIMEOUT)
        except asyncio.CancelledError:
            await self._finish(
                job, _failure(ERR_GENERATION_CANCELLED, ERR_GENERATION_CANCELLED)
            )
            raise
        except LeaseLostError:
            logger.warning(LOG_GENERATION_LEASE_LOST, post_id=job.lease.post_id)
            return None
        return await self._finish(job, outcome)

    async def _finish(
        self, job: GenerationJob, outcome: GenerationOutcome
    ) -> GenerationOutcome | None:
        try:
            await self._deps.store.finish(job.lease, outcome)
        except LeaseLostError:
            logger.warning(LOG_GENERATION_LEASE_LOST, post_id=job.lease.post_id)
            return None
        return outcome

    async def _with_heartbeat(self, job: GenerationJob) -> GenerationOutcome:
        beat = asyncio.create_task(self._heartbeat(job.lease))
        try:
            return await self._guarded(job)
        finally:
            beat.cancel()
            # ``wait`` never re-raises the beat's own outcome, so nothing from
            # the heartbeat can replace the run's result.
            await asyncio.wait([beat])

    async def _heartbeat(self, lease: GenerationLease) -> None:
        while True:
            await asyncio.sleep(self._deps.timings.heartbeat_seconds)
            try:
                await self._deps.store.heartbeat(lease)
            except LeaseLostError:
                return
            except Exception:
                # A DB blip must not kill the run: log and keep beating. A
                # persistently failing heartbeat ends in the reaper (stale).
                logger.warning(
                    LOG_HEARTBEAT_FAILED, post_id=lease.post_id, exc_info=True
                )

    async def _guarded(self, job: GenerationJob) -> GenerationOutcome:
        try:
            return await self._pipeline(job)
        except tuple(_FAILURE_CODES) as exc:
            code = _failure_code(exc)
            logger.warning(LOG_GENERATION_FAILED, post_id=job.lease.post_id, code=code)
            return _failure(code, str(exc) or code)
        except (LeaseLostError, asyncio.CancelledError):
            raise
        except Exception as exc:
            logger.exception(LOG_GENERATION_FAILED, post_id=job.lease.post_id)
            return _failure(ERR_GENERATION_FAILED, type(exc).__name__)

    async def _pipeline(self, job: GenerationJob) -> GenerationOutcome:
        if job.brief is None:
            document, titles = await self._current(job)
            languages = None
        else:
            languages = await self._write_and_gate(job, job.brief)
            document = build_generated_document(languages, _now())
            await self._store(job, document, languages)
            titles = ImageTitles(languages.title, languages.en_title)
        result = await self._deps.images.generate(
            ImageBatchRequest(
                trace=job.trace,
                subjects=missing_image_subjects(document, titles.title),
                budget_usd=self._deps.image_cost_cap_usd - job.prior_image_spend_usd,
            )
        )
        if result.images:
            await self._deps.store.merge_content(
                job.lease, _image_merge(result.images, titles)
            )
        return _outcome(job, languages, result)

    async def _current(self, job: GenerationJob) -> tuple[BlogDocument, ImageTitles]:
        content = await self._deps.store.read_content(job.lease)
        titles = job.titles or ImageTitles(job.trace.post_id, job.trace.post_id)
        return parse_blog_content(content), titles

    async def _write_and_gate(
        self, job: GenerationJob, brief: WriterBrief
    ) -> GeneratedLanguages:
        scope = BlogPhaseScope(
            project_id=job.trace.project_id,
            user_id=job.trace.user_id,
            phase=PHASE_BLOG_GENERATION,
            agent_name=AGENT_BLOG_WRITER,
        )
        with blog_phase_trace(scope):
            article = await self._deps.writer.draft(brief)
            return await self._gate(brief, article)

    async def _gate(
        self, brief: WriterBrief, article: DraftArticle
    ) -> GeneratedLanguages:
        count = brief.section_count
        pt = normalize_section_count(article.sections, count)
        en = normalize_section_count(article.en_sections, count)
        gate = self._deps.gate
        return GeneratedLanguages(
            pt=await gate.run(GateCommand(LANGUAGE_PT, pt, brief)),
            en=await gate.run(GateCommand(LANGUAGE_EN, en, brief)),
            title=article.title or brief.title,
            en_title=article.en_title or article.title or brief.title,
        )

    async def _store(
        self, job: GenerationJob, document: BlogDocument, languages: GeneratedLanguages
    ) -> None:
        written = BlogDocumentService.validate_for_write(document.to_content())
        await self._deps.store.write_content(
            job.lease,
            ContentWrite(
                content=written.content,
                featured_image_url=written.featured_image_url,
                voice_score=languages.pt.voice.overall,
                title=languages.title if job.retitle else None,
            ),
        )


def _image_merge(images: dict[str, BlogImage], titles: ImageTitles) -> ContentMerge:
    """Attach the images to whatever the row holds NOW (owner edits survive)."""

    def merge(current: dict[str, object]) -> ContentWrite:
        merged = attach_images(parse_blog_content(current), images, titles)
        written = BlogDocumentService.validate_for_write(merged.to_content())
        return ContentWrite(
            content=written.content, featured_image_url=written.featured_image_url
        )

    return merge


def _outcome(
    job: GenerationJob, languages: GeneratedLanguages | None, result: ImageBatchResult
) -> GenerationOutcome:
    status = GENERATION_STATUS_PARTIAL if result.errors else GENERATION_STATUS_COMPLETE
    logger.info(
        LOG_GENERATION_FINISHED,
        post_id=job.lease.post_id,
        project_id=job.trace.project_id,
        status=status,
        images_only=languages is None,
        voice_score=languages.pt.voice.overall if languages else None,
        voice_score_en=languages.en.voice.overall if languages else None,
        rewrite_passes=languages.pt.rewrite_passes if languages else None,
        image_count=len(result.images),
        image_spend_usd=result.spent_usd,
    )
    return GenerationOutcome(
        status=status,
        errors=result.errors,
        recoverable=bool(result.errors),
        image_count=len(result.images),
        image_spend_usd=result.spent_usd,
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "BlogGenerationDeps",
    "BlogGenerationService",
    "GenerationJob",
    "GenerationTimings",
]
