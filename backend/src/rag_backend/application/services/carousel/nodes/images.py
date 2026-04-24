"""Phase 5: parallel image generation.

Exposes two entry points:

- `run_images`: a single-node implementation used by the legacy
  `CarouselAgent._phase5_images` wrapper and by tests that drive image
  gen directly.
- `run_image_one` + `filter_image_slides`: primitives for LangGraph's
  `Send` fan-out. Each slide becomes its own graph task, which gives
  per-item checkpointing — if one slide fails partway through, the
  next resume only re-runs that slide, not the whole batch.

Both paths share the same UI contract: the frontend polls `/status`
and reads `project.phase_progress.slides`, a list of per-slide status
dicts. The fan-out path maintains that contract by updating a shared
lock-protected list captured in the build_graph closure.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from rag_backend.application.services.carousel.theme_resolver import resolve_theme
from rag_backend.application.services.carousel.types import (
    SlideData,
    short_scene,
    style_display_name,
)
from rag_backend.application.services.image_prompt_sanitizer import sanitize_image_prompt
from rag_backend.application.services.image_provider_registry import ImageProviderRegistry
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI, SLIDE_TYPE_CONTENT, SLIDE_TYPE_INTRO
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository

IMAGE_SLIDE_TYPES: frozenset[str] = frozenset({SLIDE_TYPE_INTRO, SLIDE_TYPE_CONTENT})

STATUS_PENDING = "pending"
STATUS_IN_FLIGHT = "in_flight"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


def filter_image_slides(slides: list[SlideData]) -> list[SlideData]:
    """Return only the slides that should get a hero image."""
    return [s for s in slides if s.slide_type in IMAGE_SLIDE_TYPES and s.image_prompt]


def build_initial_status(slides: list[SlideData], style_label: str) -> list[dict[str, str | int]]:
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

    done_count = 0
    progress_lock = asyncio.Lock()
    mutable_project = project

    async def _publish_progress() -> None:
        nonlocal mutable_project
        async with progress_lock:
            mutable_project.phase_progress = {
                "phase": mutable_project.status.value,
                "label": f"Generating {total} slide images in parallel — {style_label}",
                "current": done_count,
                "total": total,
                "slides": [dict(s) for s in slide_status],
            }
            mutable_project = await repo.update_project(mutable_project)

    async def _run_one(index: int, slide: SlideData) -> None:
        nonlocal done_count
        slide_status[index]["status"] = STATUS_IN_FLIGHT
        await _publish_progress()
        image_path = str(images_dir / f"slide_{slide.slide_number}.jpg")
        raw_prompt = slide.image_prompt or ""
        if project.image_model == IMAGE_MODEL_OPENAI:
            raw_prompt = sanitize_image_prompt(raw_prompt)
        final_prompt = provider.strategy.wrap(raw_prompt, theme)
        try:
            await provider.service.generate_image(
                prompt=final_prompt,
                output_path=image_path,
            )
        except Exception:
            slide_status[index]["status"] = STATUS_FAILED
            await _publish_progress()
            raise
        slide_status[index]["status"] = STATUS_DONE
        done_count += 1
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
    raw_prompt = slide.image_prompt or ""
    if project.image_model == IMAGE_MODEL_OPENAI:
        raw_prompt = sanitize_image_prompt(raw_prompt)
    final_prompt = provider.strategy.wrap(raw_prompt, theme)
    await provider.service.generate_image(prompt=final_prompt, output_path=image_path)
    return image_path
