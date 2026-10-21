"""The blog generation run: writer → quality gate → images (ADR-0025).

One run = one lease on one draft row. A full run:

1. drafts ONE continuous article (PT + EN) from the brief (``blog_generation``),
2. normalizes it to exactly N sections (N = the carousel slide count),
3. gates each language (voice score + deterministic scan + one rewrite at most)
   and checks that the EN is English (a Portuguese EN is retranslated,
   bounded; if it stays Portuguese the article is stored without EN),
4. stores the scored, image-less document (lease-fenced; refuses to overwrite
   an owner save),
5. generates the empty image slots (cover + N sections, ``blog_section_image``)
   within what is left of the post's image budget, best-effort,
6. attaches the images by slot id to the row's CURRENT content (an owner edit
   made during the image step is kept; a section deleted meanwhile is skipped)
   and finishes ``complete`` or ``partial``.

An images-only job (a retry of a post whose article exists) skips 1-4. Each
stage has its own budget: 1-3 ``BLOG_GENERATION_TEXT_TIMEOUT_SECONDS``
(timeout → ``failed``), 5 ``BLOG_IMAGE_WAVE_TIMEOUT_SECONDS`` per image wave
(timeout → the finished images are kept and the run ends ``partial``, so the
retry is images-only). The run heartbeats while it works; a heartbeat failure
is logged and never ends the run. A writer/count/document failure finishes
``failed`` without storing anything as if valid; cancellation finishes
``failed`` + recoverable and re-raises. A lost lease stops the run silently.
The post always stays a draft.

_FAILURE_CODES lists the failures that end a run as failed and recoverable (the owner
retries); a TimeoutError means the text-stage budget ran out and nothing was stored.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from rag_backend.application.services.blog.blog_document_service import (
    BlogDocumentService,
)
from rag_backend.application.services.blog.blog_english_gate import EnglishCheck
from rag_backend.application.services.blog.blog_generated_document import (
    GeneratedLanguages,
    ImageTitles,
    attach_images,
    build_generated_document,
    missing_image_subjects,
    placed_slots,
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
    ERR_EN_WRONG_LANGUAGE,
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
    TRACE_INPUT_POST_ID,
    TRACE_INPUT_SECTION_COUNT,
    TRACE_INPUT_TITLE,
    TRACE_OUTPUT_SECTION_COUNT,
    TRACE_OUTPUT_VOICE_SCORE,
)
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_OUTPUT_STATUS_COMPLETED,
    TRACE_STATUS_FIELD,
)
from rag_backend.domain.models.blog_document import (
    BlogDocument,
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import (
    DocumentApply,
    DraftArticle,
    GatedLanguage,
    GenerationConflictError,
    GenerationLease,
    GenerationOutcome,
    LeaseLostError,
    SectionCountMismatchError,
    WriterBrief,
    WriterFailedError,
)

logger = structlog.get_logger(__name__)

_FAILURE_CODES: dict[type[Exception], str] = {
    WriterFailedError: ERR_GENERATION_LLM_FAILED,
    SectionCountMismatchError: ERR_SECTION_COUNT_MISMATCH,
    InvalidBlogDocumentError: ERR_INVALID_GENERATED_DOCUMENT,
    GenerationConflictError: ERR_GENERATION_CONFLICT,
    TimeoutError: ERR_GENERATION_TIMEOUT,
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
            outcome = await self._with_heartbeat(job)
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
        """Run the pipeline while a heartbeat keeps the lease fresh.

        wait never re-raises the beat's own outcome, so nothing from the heartbeat can
        replace the run's result.
        """
        beat = asyncio.create_task(self._heartbeat(job.lease))
        try:
            return await self._guarded(job)
        finally:
            beat.cancel()
            await asyncio.wait([beat])

    async def _heartbeat(self, lease: GenerationLease) -> None:
        """Beat the lease until cancelled.

        A DB blip must not kill the run: it is logged and the beat continues. A
        persistently failing heartbeat ends in the reaper (stale).
        """
        while True:
            await asyncio.sleep(self._deps.timings.heartbeat_seconds)
            try:
                await self._deps.store.heartbeat(lease)
            except LeaseLostError:
                return
            except Exception:
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
        """Write the article, then generate and store its images.

        The image budget is reserved under the row lock before any provider spend and
        kept even when a slot later fails, since it may be billed.
        """
        if job.brief is None:
            document, titles = await self._current(job)
            languages = None
        else:
            languages = await self._write_and_gate(job, job.brief)
            document = build_generated_document(languages, _now())
            await self._store(job, document, languages)
            titles = ImageTitles(languages.title, languages.en_title)
        subjects = missing_image_subjects(document, titles.title)
        granted = await self._deps.store.reserve_images(job.lease, len(subjects))
        result = await self._deps.images.generate(
            ImageBatchRequest(
                trace=job.trace,
                subjects=subjects,
                max_images=granted,
                wave_seconds=self._deps.timings.image_wave_seconds,
            )
        )
        if result.images:
            await self._attach(job, result, titles)
        return _outcome(job, languages, result)

    async def _attach(
        self, job: GenerationJob, result: ImageBatchResult, titles: ImageTitles
    ) -> None:
        """Attach by section id onto the LATEST document (owner edits survive);
        a failed write deletes the new files, and so does a successful write for
        the images whose slot the owner removed or filled meanwhile."""
        images = result.images
        placed: set[str] = set()

        def edit(latest: BlogDocument) -> BlogDocument:
            attached = attach_images(latest, images, titles)
            placed.clear()
            placed.update(placed_slots(attached, images))
            return attached

        await self._deps.store.apply_document(
            job.lease,
            DocumentApply(
                edit=edit,
                images_generated=len(images),
                discard=lambda: self._deps.images.discard(job.lease.post_id, images),
            ),
        )
        unused = {slot: image for slot, image in images.items() if slot not in placed}
        self._deps.images.discard(job.lease.post_id, unused)

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
        brief_input = {
            TRACE_INPUT_POST_ID: job.lease.post_id,
            TRACE_INPUT_TITLE: brief.title,
            TRACE_INPUT_SECTION_COUNT: brief.section_count,
        }
        with blog_phase_trace(scope, trace_input=brief_input) as trace:
            async with asyncio.timeout(self._deps.timings.text_timeout_seconds):
                article = await self._deps.writer.draft(brief)
                pt, en = await self._gate(brief, article)
                english = await self._deps.english.ensure(
                    EnglishCheck(job.lease.post_id, pt, en, brief)
                )
            trace.set_output({
                TRACE_STATUS_FIELD: TRACE_OUTPUT_STATUS_COMPLETED,
                TRACE_OUTPUT_SECTION_COUNT: brief.section_count,
                TRACE_OUTPUT_VOICE_SCORE: pt.voice.overall,
            })
        return GeneratedLanguages(
            pt=pt,
            en=english,
            title=article.title or brief.title,
            en_title=article.en_title or article.title or brief.title,
        )

    async def _gate(
        self, brief: WriterBrief, article: DraftArticle
    ) -> tuple[GatedLanguage, GatedLanguage]:
        count = brief.section_count
        pt = normalize_section_count(article.sections, count)
        en = normalize_section_count(article.en_sections, count)
        gate = self._deps.gate
        return (
            await gate.run(GateCommand(LANGUAGE_PT, pt, brief)),
            await gate.run(GateCommand(LANGUAGE_EN, en, brief)),
        )

    async def _store(
        self, job: GenerationJob, document: BlogDocument, languages: GeneratedLanguages
    ) -> None:
        BlogDocumentService.validate_for_write(document.to_content())
        await self._deps.store.apply_document(
            job.lease,
            DocumentApply(
                edit=lambda latest: _place_article(latest, document),
                voice_score=languages.pt.voice.overall,
                replaces_document=True,
            ),
        )


def _place_article(latest: BlogDocument, article: BlogDocument) -> BlogDocument:
    """The generated article replaces the in-progress bootstrap document; an
    article the owner already wrote is never overwritten (conflict)."""
    if any(section.body_md.strip() for section in latest.sections):
        raise GenerationConflictError(ERR_GENERATION_CONFLICT)
    return article


def _outcome(
    job: GenerationJob, languages: GeneratedLanguages | None, result: ImageBatchResult
) -> GenerationOutcome:
    """Build the run outcome; a standalone post takes the writer's title."""
    errors = (*_language_errors(languages), *result.errors)
    status = GENERATION_STATUS_PARTIAL if errors else GENERATION_STATUS_COMPLETE
    logger.info(
        LOG_GENERATION_FINISHED,
        post_id=job.lease.post_id,
        project_id=job.trace.project_id,
        status=status,
        images_only=languages is None,
        voice_score=languages.pt.voice.overall if languages else None,
        voice_score_en=_en_score(languages),
        rewrite_passes=languages.pt.rewrite_passes if languages else None,
        image_count=len(result.images),
    )
    return GenerationOutcome(
        status=status,
        errors=errors,
        recoverable=bool(errors),
        image_count=len(result.images),
        title=languages.title if job.retitle and languages else None,
    )


def _language_errors(
    languages: GeneratedLanguages | None,
) -> tuple[dict[str, object], ...]:
    """``en_translation_wrong_language`` when the EN could not be made English."""
    if languages is None or languages.en is not None:
        return ()
    return ({ERROR_KEY_CODE: ERR_EN_WRONG_LANGUAGE, ERROR_KEY_REASON: LANGUAGE_EN},)


def _en_score(languages: GeneratedLanguages | None) -> float | None:
    if languages is None or languages.en is None:
        return None
    return languages.en.voice.overall


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "BlogGenerationDeps",
    "BlogGenerationService",
    "GenerationJob",
    "GenerationTimings",
]
