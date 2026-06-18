"""Phase 5: parallel image generation.

Exposes entry points used by the editorial workflow image phase and tests:

- `run_images`: batch image generation for a slide list.
- `run_image_one` + `filter_image_slides`: primitives for LangGraph's
  `Send` fan-out with per-slide checkpointing.

Both paths share the UI contract: progress is persisted on the project row
(`phase_progress.slides`) for the create workspace SSE stream.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from rag_backend.application.services.carousel.editorial_workflow_support import (
    publish_workflow_progress,
)
from rag_backend.application.services.carousel.image_generation_constants import (
    DEFAULT_IMAGE_CONCURRENCY,
    DEFAULT_IMAGE_MAX_ATTEMPTS,
    ERR_IMAGE_BATCH_PARTIAL,
    LOG_IMAGE_BATCH_PARTIAL_FAILURE,
    LOG_IMAGE_RATE_LIMITED,
)
from rag_backend.application.services.carousel.image_generation_records import (
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_RECOVERED,
    GENERATION_STATUS_REUSED,
    GENERATION_STATUS_SUCCEEDED,
    ImageGenerationRecordInput,
    file_sha256,
    reuse_recorded_generation,
    upsert_generation_record,
)
from rag_backend.application.services.carousel.image_prompt_package import (
    METADATA_CONTENT_SHA,
    METADATA_GENERATION_KEY,
    METADATA_MODEL,
    METADATA_PROMPT_SHA,
    METADATA_PROVIDER,
    METADATA_RAW_PROMPT,
    METADATA_RENDERED_PROMPT,
    METADATA_STYLE,
    ImagePromptPackage,
    ImagePromptPackageRequest,
    render_image_prompt_package,
)
from rag_backend.application.services.carousel.image_rate_limit import (
    RetryEvent,
    RetryOptions,
    build_image_semaphore,
    generate_with_retry_after,
)
from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import (
    SlideData,
    short_scene,
    style_display_name,
)
from rag_backend.domain.constants import (
    CAROUSEL_STATUS_GENERATING_IMAGES,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_IMAGES
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.external.openai_image import (
    _openai_status_error_detail,
)
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.presentation import (
    ImageProvider,
    ImageProviderPort,
    ProgressSnapshot,
    WorkflowProgressPort,
)

logger = get_logger()

IMAGE_SLIDE_TYPES: frozenset[str] = frozenset({
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CLOSING,
})

STATUS_PENDING = "pending"
STATUS_IN_FLIGHT = "in_flight"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

_PNG_MAGIC = b"\x89PNG"
_ERR_INVALID_IMAGE = "Generated image is not a valid JPEG: {}"


@dataclass
class ImageGenerationConfig:
    """Configuration for image generation operations."""

    project: CarouselProject
    slides: list[SlideData] | None = None
    slide: SlideData | None = None
    output_dir: Path | None = None
    repo: CarouselRepository | None = None
    image_registry: ImageProviderPort | None = None
    # AE-0121: presentation→editorial progress CALLBACK port. When the editorial
    # workflow injects it, the image node reports progress through it and editorial
    # owns the workflow-state ``phase_progress`` write + SSE. When absent (direct
    # callers / unit tests), the node falls back to the legacy in-node write so
    # behavior is byte-identical.
    progress_port: WorkflowProgressPort | None = None
    # AE-0208: provider-rate-limit controls. When None, the run resolves them
    # from settings (org cap of 5/min → concurrency 5; 5 retry-after-honoring
    # attempts). Tests inject small values for fast, deterministic coverage.
    concurrency: int | None = None
    max_attempts: int | None = None


@dataclass(frozen=True)
class SlideImageMetadataUpdate:
    slide: CarouselSlide
    image_path: str
    prompt: ImagePromptPackage
    project: CarouselProject


def _ensure_jpeg_format(image_path: str) -> str:
    """Convert PNG image data to JPEG if the file was saved with a .jpg extension.

    Some providers (e.g. OpenAI DALL-E) return PNG bytes but the pipeline
    hardcodes a .jpg path. Re-encode to JPEG so content-type and extension agree.
    """
    path = Path(image_path)
    if not path.exists():
        return image_path
    with path.open("rb") as f:
        header = f.read(4)
    try:
        from PIL import Image as PILImage

        if header == _PNG_MAGIC:
            with PILImage.open(path) as img:
                if img.mode in {"RGBA", "P"}:
                    img = img.convert("RGB")
                img.save(path, "JPEG", quality=95)
        with PILImage.open(path) as img:
            image_format = img.format
            img.verify()
    except Exception as exc:
        raise RuntimeError(_ERR_INVALID_IMAGE.format(path)) from exc
    if image_format != "JPEG":
        raise RuntimeError(_ERR_INVALID_IMAGE.format(path))
    return image_path


def _candidate_image_paths(slide: CarouselSlide, image_path: str) -> tuple[Path, ...]:
    path_value = slide.image_path
    if isinstance(path_value, str) and path_value.strip():
        return (Path(path_value), Path(image_path))
    return (Path(image_path),)


def _reuse_existing_image(
    slide: CarouselSlide,
    prompt: ImagePromptPackage,
    image_path: str,
) -> str | None:
    stored_key = slide.metadata.get(METADATA_GENERATION_KEY)
    if isinstance(stored_key, str) and stored_key != prompt.generation_key:
        return None
    for candidate in _candidate_image_paths(slide, image_path):
        if not candidate.is_file():
            continue
        try:
            return _ensure_jpeg_format(str(candidate))
        except RuntimeError:
            continue
    return None


def _apply_image_metadata(update: SlideImageMetadataUpdate) -> None:
    metadata = dict(update.slide.metadata or {})
    metadata.update({
        METADATA_CONTENT_SHA: file_sha256(update.image_path),
        METADATA_GENERATION_KEY: update.prompt.generation_key,
        METADATA_MODEL: update.project.image_model,
        METADATA_PROMPT_SHA: update.prompt.prompt_hash,
        METADATA_PROVIDER: update.project.image_model,
        METADATA_RAW_PROMPT: update.prompt.raw_prompt,
        METADATA_RENDERED_PROMPT: update.prompt.rendered_prompt,
        METADATA_STYLE: update.project.image_style,
    })
    update.slide.metadata = metadata


def filter_image_slides(slides: list[SlideData]) -> list[SlideData]:
    """Return only the slides that should get a hero image."""
    return [s for s in slides if s.slide_type in IMAGE_SLIDE_TYPES and s.image_prompt]


def build_initial_status(
    slides: list[SlideData], style_label: str
) -> list[dict[str, str | int]]:
    """Initial all-pending snapshot for the per-slide UI checklist."""
    return [
        {
            "number": s.slide_number,
            "status": STATUS_PENDING,
            "style": style_label,
            "scene": short_scene(s.image_prompt or ""),
        }
        for s in slides
    ]


@dataclass
class _ErrorContext:
    """Context for image generation error handling."""

    project: CarouselProject
    slide: SlideData
    prompt: ImagePromptPackage
    image_path: str
    persisted_slide: CarouselSlide | None
    repo: CarouselRepository
    index: int
    slide_status: list[dict[str, object]]
    progress_publisher: Callable[[], Awaitable[None]] | None = None


@dataclass
class _PersistContext:
    """Context for persisting a generated image."""

    persisted_slide: CarouselSlide
    image_path: str
    prompt: ImagePromptPackage
    generation_status: str
    project: CarouselProject
    repo: CarouselRepository
    lock: asyncio.Lock


async def _generate_new_image(
    provider: ImageProvider,
    prompt: ImagePromptPackage,
    image_path: str,
) -> None:
    """Generate a new image and ensure it is JPEG."""
    await provider.service.generate_image(
        prompt=prompt.rendered_prompt,
        output_path=image_path,
    )
    _ensure_jpeg_format(image_path)


async def _handle_generation_error(
    exc: Exception,
    ctx: _ErrorContext,
) -> None:
    """Log the error, record failure, update status, and re-raise."""
    error_details: dict[str, object] | None = None
    from openai import APIStatusError

    if isinstance(exc, APIStatusError):
        error_details = _openai_status_error_detail(exc)
    logger.error(
        "carousel_image_generation_failed",
        project_id=str(ctx.project.id),
        slide_id=str(ctx.persisted_slide.id) if ctx.persisted_slide else None,
        slide_number=ctx.slide.slide_number,
        provider=ctx.prompt.provider,
        model=ctx.prompt.model,
        generation_key=ctx.prompt.generation_key,
        prompt_hash=ctx.prompt.prompt_hash,
        image_style=ctx.project.image_style,
        output_path=ctx.image_path,
        error=str(exc),
        exc_info=True,
    )
    ctx.slide_status[ctx.index]["status"] = STATUS_FAILED
    if ctx.progress_publisher is not None:
        await ctx.progress_publisher()
    if ctx.persisted_slide is not None:
        await upsert_generation_record(
            ctx.repo,
            ImageGenerationRecordInput(
                project=ctx.project,
                slide=ctx.persisted_slide,
                prompt=ctx.prompt,
                status=GENERATION_STATUS_FAILED,
                image_path=ctx.image_path,
                error_message=str(exc),
                error_details=error_details,
            ),
        )
    raise


async def _persist_slide_image(ctx: _PersistContext) -> None:
    """Update the slide image path, metadata, and generation record."""
    async with ctx.lock:
        ctx.persisted_slide.image_path = ctx.image_path
        _apply_image_metadata(
            SlideImageMetadataUpdate(
                slide=ctx.persisted_slide,
                image_path=ctx.image_path,
                prompt=ctx.prompt,
                project=ctx.project,
            )
        )
        await ctx.repo.update_slide(ctx.persisted_slide)
        await upsert_generation_record(
            ctx.repo,
            ImageGenerationRecordInput(
                project=ctx.project,
                slide=ctx.persisted_slide,
                prompt=ctx.prompt,
                status=ctx.generation_status,
                image_path=ctx.image_path,
            ),
        )


def _make_retry_logger(
    project: CarouselProject,
    slide: SlideData,
) -> Callable[[RetryEvent], None]:
    """Build an ``on_retry`` callback that logs a provider rate-limit retry.

    AE-0208: keeps the (infrastructure-aware) logging in the image node while the
    retry helper itself stays infrastructure-free.
    """

    def _log(event: RetryEvent) -> None:
        logger.warning(
            LOG_IMAGE_RATE_LIMITED,
            project_id=str(project.id),
            slide_number=slide.slide_number,
            attempt=event.attempt,
            max_attempts=event.max_attempts,
            wait_seconds=event.wait_seconds,
            retry_after=event.retry_after,
        )

    return _log


def _log_reuse(
    project: CarouselProject,
    slide: SlideData,
    path: str,
) -> None:
    """Log that an existing image was reused."""
    logger.info(
        "carousel_image_generation_reused",
        project_id=str(project.id),
        slide_number=slide.slide_number,
        image_path=path,
    )


@dataclass
class _ImageRunContext:
    """Mutable state shared across parallel image generation tasks."""

    project: CarouselProject
    repo: CarouselRepository
    provider: ImageProvider
    theme: dict[str, str]
    images_dir: Path
    slides_by_number: dict[int, CarouselSlide]
    total: int
    style_label: str
    slides_with_images: list[SlideData]
    slide_status: list[dict[str, object]]
    done_count: int
    progress_lock: asyncio.Lock
    mutable_project: CarouselProject
    progress_port: WorkflowProgressPort | None
    semaphore: asyncio.Semaphore
    max_attempts: int


def _resolve_rate_limit_settings(
    config: ImageGenerationConfig,
) -> tuple[int, int]:
    """Resolve (concurrency, max_attempts) for the run.

    AE-0208: caps concurrent provider calls at the documented per-minute org cap
    and bounds the retry-after-honoring attempt budget. Explicit config values
    win (the infrastructure-aware editorial pipeline injects the settings-backed
    values; tests inject small, fast values). When absent, the application-layer
    defaults apply so direct callers stay capped without reaching infrastructure.
    """
    concurrency = (
        config.concurrency
        if config.concurrency is not None
        else DEFAULT_IMAGE_CONCURRENCY
    )
    max_attempts = (
        config.max_attempts
        if config.max_attempts is not None
        else DEFAULT_IMAGE_MAX_ATTEMPTS
    )
    return concurrency, max_attempts


async def _build_image_run_context(
    config: ImageGenerationConfig,
) -> _ImageRunContext:
    """Build mutable state from a validated config."""
    project = config.project
    images_dir = config.output_dir / "images"  # type: ignore[operator]
    images_dir.mkdir(parents=True, exist_ok=True)

    theme = resolve_theme(project)
    provider = config.image_registry.resolve(  # type: ignore[union-attr]
        project.image_model, project.image_style
    )

    slides_with_images = filter_image_slides(config.slides)  # type: ignore[arg-type]
    total = len(slides_with_images)
    style_label = style_display_name(project.image_model, project.image_style)
    slide_status = build_initial_status(slides_with_images, style_label)

    db_slides = await config.repo.get_slides_by_project(project.id)  # type: ignore[union-attr]
    slides_by_number = {s.slide_number: s for s in db_slides}

    concurrency, max_attempts = _resolve_rate_limit_settings(config)

    return _ImageRunContext(
        project=project,
        repo=config.repo,  # type: ignore[arg-type]
        provider=provider,
        theme=theme,
        images_dir=images_dir,
        slides_by_number=slides_by_number,
        total=total,
        style_label=style_label,
        slides_with_images=slides_with_images,
        slide_status=slide_status,
        done_count=0,
        progress_lock=asyncio.Lock(),
        mutable_project=project,
        progress_port=config.progress_port,
        semaphore=build_image_semaphore(concurrency),
        max_attempts=max_attempts,
    )


def _build_progress_snapshot(ctx: _ImageRunContext) -> ProgressSnapshot:
    """Build the progress snapshot (the byte-identical ``phase_progress`` payload).

    The fields map one-to-one onto the dict the legacy in-node write persisted, so
    whichever path consumes it — the editorial callback or the legacy in-node
    write — produces the identical ``phase_progress`` column + SSE payload.
    """
    return ProgressSnapshot(
        project_id=str(ctx.mutable_project.id),
        phase=CAROUSEL_STATUS_GENERATING_IMAGES,
        sse_phase=PHASE_IMAGES,
        label=(f"Generating {ctx.total} slide images in parallel — {ctx.style_label}"),
        current=ctx.done_count,
        total=ctx.total,
        slides=tuple(dict(s) for s in ctx.slide_status),
    )


async def _publish_progress_state(ctx: _ImageRunContext) -> None:
    """Report the progress snapshot via the callback port, or write it in-node.

    AE-0121: when the editorial workflow injected a :class:`WorkflowProgressPort`,
    the presentation image node reports a :class:`ProgressSnapshot` through it and
    EDITORIAL owns the workflow-state ``phase_progress`` write + SSE emission
    (presentation does not write workflow state). When no port is injected (direct
    callers / unit tests), the node falls back to the byte-identical legacy in-node
    write so behavior is preserved exactly.
    """
    async with ctx.progress_lock:
        snapshot = _build_progress_snapshot(ctx)
        if ctx.progress_port is not None:
            await ctx.progress_port.report_progress(snapshot)
            return
        ctx.mutable_project.phase_progress = snapshot.as_phase_progress()
        ctx.mutable_project = await ctx.repo.update_project(ctx.mutable_project)
        await publish_workflow_progress(
            str(ctx.mutable_project.id),
            PHASE_IMAGES,
            dict(ctx.mutable_project.phase_progress or {}),
        )


async def _run_one_image(
    index: int,
    slide: SlideData,
    ctx: _ImageRunContext,
) -> None:
    """Generate an image for one slide and persist the result."""
    ctx.slide_status[index]["status"] = STATUS_IN_FLIGHT
    await _publish_progress_state(ctx)

    image_path = str(ctx.images_dir / f"slide_{slide.slide_number}.jpg")
    prompt = render_image_prompt_package(
        ImagePromptPackageRequest(
            project=ctx.project,
            slide=slide,
            theme=ctx.theme,
        )
    )
    persisted_slide = ctx.slides_by_number.get(slide.slide_number)
    recorded_path = await reuse_recorded_generation(ctx.repo, prompt)
    legacy_path = (
        _reuse_existing_image(persisted_slide, prompt, image_path)
        if persisted_slide is not None
        else None
    )
    reused_path = recorded_path or legacy_path
    generation_status = (
        GENERATION_STATUS_REUSED
        if recorded_path
        else GENERATION_STATUS_RECOVERED
        if reused_path
        else GENERATION_STATUS_SUCCEEDED
    )
    if reused_path is None:
        try:
            async with ctx.semaphore:
                await generate_with_retry_after(
                    lambda: _generate_new_image(ctx.provider, prompt, image_path),
                    RetryOptions(
                        max_attempts=ctx.max_attempts,
                        on_retry=_make_retry_logger(ctx.project, slide),
                    ),
                )
        except Exception as exc:
            await _handle_generation_error(
                exc,
                _ErrorContext(
                    project=ctx.project,
                    slide=slide,
                    prompt=prompt,
                    image_path=image_path,
                    persisted_slide=persisted_slide,
                    repo=ctx.repo,
                    index=index,
                    slide_status=ctx.slide_status,
                    progress_publisher=lambda: _publish_progress_state(ctx),
                ),
            )
    else:
        image_path = reused_path
        _log_reuse(ctx.project, slide, image_path)

    ctx.slide_status[index]["status"] = STATUS_DONE
    ctx.done_count += 1
    if persisted_slide is not None:
        await _persist_slide_image(
            _PersistContext(
                persisted_slide=persisted_slide,
                image_path=image_path,
                prompt=prompt,
                generation_status=generation_status,
                project=ctx.project,
                repo=ctx.repo,
                lock=ctx.progress_lock,
            ),
        )
    await _publish_progress_state(ctx)


async def run_images(
    config: ImageGenerationConfig,
) -> None:
    """Single-node parallel image gen using asyncio.gather (no LangGraph)."""
    if config.slides is None:
        msg = "slides must be provided"
        raise ValueError(msg)
    if config.output_dir is None:
        msg = "output_dir must be provided"
        raise ValueError(msg)
    if config.repo is None:
        msg = "repo must be provided"
        raise ValueError(msg)
    if config.image_registry is None:
        msg = "image_registry must be provided"
        raise ValueError(msg)

    ctx = await _build_image_run_context(config)

    await _publish_progress_state(ctx)
    # AE-0209: per-slide partial commit. ``return_exceptions=True`` lets every
    # slide run to completion instead of one failure cancelling its siblings;
    # each ``_run_one_image`` commits its own slide on success, so successful
    # images persist to workflow state even when another slide fails. The phase
    # is idempotent on re-run (reused by ``prompt_hash`` / generation_key), so a
    # retry regenerates only the still-missing slides and completes.
    results = await asyncio.gather(
        *[_run_one_image(i, s, ctx) for i, s in enumerate(ctx.slides_with_images)],
        return_exceptions=True,
    )
    _raise_on_batch_failures(results, ctx.total)


def _raise_on_batch_failures(
    results: list[BaseException | None],
    total: int,
) -> None:
    """Re-raise after a batch if any slide failed (successes already committed).

    ``CancelledError`` is propagated immediately so a cancelled batch is never
    masked as a recoverable partial failure. Otherwise the first slide exception
    is chained onto an aggregate error that records how many slides failed.
    """
    failures = [r for r in results if isinstance(r, BaseException)]
    if not failures:
        return
    for failure in failures:
        if isinstance(failure, asyncio.CancelledError):
            raise failure
    logger.error(
        LOG_IMAGE_BATCH_PARTIAL_FAILURE,
        failed=len(failures),
        total=total,
    )
    message = ERR_IMAGE_BATCH_PARTIAL.format(failed=len(failures), total=total)
    raise RuntimeError(message) from failures[0]


async def run_image_one(
    config: ImageGenerationConfig,
) -> str:
    """Generate a single slide image. Returns the output path.

    Used by the LangGraph Send fan-out worker — progress tracking is
    handled by the enclosing graph node, not by this function.
    """
    if config.project is None:
        msg = "project must be provided"
        raise ValueError(msg)
    if config.slide is None:
        msg = "slide must be provided"
        raise ValueError(msg)
    if config.output_dir is None:
        msg = "output_dir must be provided"
        raise ValueError(msg)
    if config.image_registry is None:
        msg = "image_registry must be provided"
        raise ValueError(msg)
    images_dir = config.output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    theme = resolve_theme(config.project)
    provider = config.image_registry.resolve(
        config.project.image_model, config.project.image_style
    )
    image_path = str(images_dir / f"slide_{config.slide.slide_number}.jpg")
    prompt = render_image_prompt_package(
        ImagePromptPackageRequest(
            project=config.project,
            slide=config.slide,
            theme=theme,
        )
    )
    try:
        await provider.service.generate_image(
            prompt=prompt.rendered_prompt,
            output_path=image_path,
        )
        _ensure_jpeg_format(image_path)
    except Exception as exc:
        logger.error(
            "carousel_image_generation_failed",
            project_id=str(config.project.id),
            slide_number=config.slide.slide_number,
            provider=prompt.provider,
            model=prompt.model,
            generation_key=prompt.generation_key,
            prompt_hash=prompt.prompt_hash,
            image_style=config.project.image_style,
            output_path=image_path,
            error=str(exc),
            exc_info=True,
        )
        raise
    return image_path
