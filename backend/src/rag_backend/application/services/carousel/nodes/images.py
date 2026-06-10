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
from dataclasses import dataclass
from pathlib import Path

from rag_backend.application.services.carousel.editorial_workflow_support import (
    publish_workflow_progress,
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
from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import (
    SlideData,
    short_scene,
    style_display_name,
)
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
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

logger = get_logger()

IMAGE_SLIDE_TYPES: frozenset[str] = frozenset(
    {
        SLIDE_TYPE_INTRO,
        SLIDE_TYPE_SUMMARY,
        SLIDE_TYPE_CONTENT,
        SLIDE_TYPE_CLOSING,
    }
)

STATUS_PENDING = "pending"
STATUS_IN_FLIGHT = "in_flight"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

_PNG_MAGIC = b"\x89PNG"
_ERR_INVALID_IMAGE = "Generated image is not a valid JPEG: {}"


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
    metadata.update(
        {
            METADATA_CONTENT_SHA: file_sha256(update.image_path),
            METADATA_GENERATION_KEY: update.prompt.generation_key,
            METADATA_MODEL: update.project.image_model,
            METADATA_PROMPT_SHA: update.prompt.prompt_hash,
            METADATA_PROVIDER: update.project.image_model,
            METADATA_RAW_PROMPT: update.prompt.raw_prompt,
            METADATA_RENDERED_PROMPT: update.prompt.rendered_prompt,
            METADATA_STYLE: update.project.image_style,
        }
    )
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


async def run_images(
    project: CarouselProject,
    slides: list[SlideData],
    output_dir: Path,
    *,
    repo: CarouselRepository,
    image_registry: ImageProviderRegistry,
) -> None:
    """Single-node parallel image gen using asyncio.gather (no LangGraph)."""
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    theme = resolve_theme(project)
    provider = image_registry.resolve(project.image_model, project.image_style)

    slides_with_images = filter_image_slides(slides)
    total = len(slides_with_images)
    style_label = style_display_name(project.image_model, project.image_style)
    slide_status = build_initial_status(slides_with_images, style_label)
    db_slides = await repo.get_slides_by_project(project.id)
    slides_by_number = {slide.slide_number: slide for slide in db_slides}

    done_count = 0
    progress_lock = asyncio.Lock()
    mutable_project = project

    async def _publish_progress() -> None:
        nonlocal mutable_project
        async with progress_lock:
            mutable_project.phase_progress = {
                "phase": CAROUSEL_STATUS_GENERATING_IMAGES,
                "label": f"Generating {total} slide images in parallel — {style_label}",
                "current": done_count,
                "total": total,
                "slides": [dict(s) for s in slide_status],
            }
            mutable_project = await repo.update_project(mutable_project)
            await publish_workflow_progress(
                str(mutable_project.id),
                PHASE_IMAGES,
                dict(mutable_project.phase_progress or {}),
            )

    async def _run_one(index: int, slide: SlideData) -> None:
        nonlocal done_count
        slide_status[index]["status"] = STATUS_IN_FLIGHT
        await _publish_progress()
        image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
        prompt = render_image_prompt_package(
            ImagePromptPackageRequest(
                project=project,
                slide=slide,
                theme=theme,
            )
        )
        persisted_slide = slides_by_number.get(slide.slide_number)
        recorded_path = await reuse_recorded_generation(repo, prompt)
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
                await provider.service.generate_image(
                    prompt=prompt.rendered_prompt,
                    output_path=image_path,
                )
                _ensure_jpeg_format(image_path)
            except Exception as exc:
                error_details: dict[str, object] | None = None
                from openai import APIStatusError

                if isinstance(exc, APIStatusError):
                    error_details = _openai_status_error_detail(exc)
                logger.error(
                    "carousel_image_generation_failed",
                    project_id=str(project.id),
                    slide_id=str(persisted_slide.id) if persisted_slide else None,
                    slide_number=slide.slide_number,
                    provider=prompt.provider,
                    model=prompt.model,
                    generation_key=prompt.generation_key,
                    prompt_hash=prompt.prompt_hash,
                    image_style=project.image_style,
                    output_path=image_path,
                    error=str(exc),
                    exc_info=True,
                )
                slide_status[index]["status"] = STATUS_FAILED
                if persisted_slide is not None:
                    await upsert_generation_record(
                        repo,
                        ImageGenerationRecordInput(
                            project=project,
                            slide=persisted_slide,
                            prompt=prompt,
                            status=GENERATION_STATUS_FAILED,
                            image_path=image_path,
                            error_message=str(exc),
                            error_details=error_details,
                        ),
                    )
                await _publish_progress()
                raise
        else:
            image_path = reused_path
            logger.info(
                "carousel_image_generation_reused",
                project_id=str(project.id),
                slide_number=slide.slide_number,
                image_path=image_path,
            )
        slide_status[index]["status"] = STATUS_DONE
        done_count += 1
        if persisted_slide is not None:
            async with progress_lock:
                persisted_slide.image_path = image_path
                _apply_image_metadata(
                    SlideImageMetadataUpdate(
                        slide=persisted_slide,
                        image_path=image_path,
                        prompt=prompt,
                        project=project,
                    )
                )
                await repo.update_slide(persisted_slide)
                await upsert_generation_record(
                    repo,
                    ImageGenerationRecordInput(
                        project=project,
                        slide=persisted_slide,
                        prompt=prompt,
                        status=generation_status,
                        image_path=image_path,
                    ),
                )
        await _publish_progress()

    await _publish_progress()
    await asyncio.gather(*[_run_one(i, s) for i, s in enumerate(slides_with_images)])


async def run_image_one(
    project: CarouselProject,
    slide: SlideData,
    output_dir: Path,
    *,
    image_registry: ImageProviderRegistry,
) -> str:
    """Generate a single slide image. Returns the output path.

    Used by the LangGraph Send fan-out worker — progress tracking is
    handled by the enclosing graph node, not by this function.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    theme = resolve_theme(project)
    provider = image_registry.resolve(project.image_model, project.image_style)
    image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
    prompt = render_image_prompt_package(
        ImagePromptPackageRequest(
            project=project,
            slide=slide,
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
            project_id=str(project.id),
            slide_number=slide.slide_number,
            provider=prompt.provider,
            model=prompt.model,
            generation_key=prompt.generation_key,
            prompt_hash=prompt.prompt_hash,
            image_style=project.image_style,
            output_path=image_path,
            error=str(exc),
            exc_info=True,
        )
        raise
    return image_path
