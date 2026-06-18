"""Design and image generation helpers for the editorial workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_progress_reporter import (
    EditorialProgressReporter,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.images import (
    ImageGenerationConfig,
    run_images,
)
from rag_backend.application.services.carousel.outline_normalize import (
    canonical_slide_type,
)
from rag_backend.application.services.carousel.types import (
    MAX_SLIDES,
    SlideData,
    unpack_extras,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.models import CarouselSlide
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)


@dataclass(frozen=True)
class CarouselImageGenerationContext:
    """Inputs for generating carousel hero and slide images."""

    project_id: str
    slides: list[SlideData]
    image_registry: ImageProviderRegistry


def _slide_data_from_outline_item(
    item: dict[str, object],
    index: int,
) -> SlideData | None:
    slide_number = int(item.get("slide_index", index + 1))
    heading = str(item.get("title", ""))
    key_points = item.get("key_points", [])
    body_parts = [
        str(point) for point in key_points if isinstance(point, (str, int, float))
    ]
    body = " · ".join(body_parts) if body_parts else heading
    raw_type = item.get("slide_type")
    slide_type = (
        str(raw_type)
        if isinstance(raw_type, str) and raw_type.strip()
        else canonical_slide_type(slide_number)
    )
    image_prompt = f"Editorial illustration for carousel slide: {heading}"
    return SlideData(
        slide_number=slide_number,
        slide_type=slide_type,
        heading=heading,
        body=body,
        image_prompt=image_prompt,
    )


async def _persist_outline_slide(
    repo: PostgresCarouselRepository,
    project_id: UUID,
    data: SlideData,
) -> None:
    slide = CarouselSlide(
        project_id=project_id,
        slide_number=data.slide_number,
        slide_type=data.slide_type,
        heading=data.heading,
        body=data.body,
        image_prompt=data.image_prompt,
    )
    await repo.create_slide(slide)


async def ensure_slides_from_outline(
    db: AsyncSession,
    project_id: str,
    outline: list[dict[str, object]],
) -> list[SlideData]:
    """Persist outline entries as carousel slides when none exist yet."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None:
        return []
    existing = await repo.get_slides_by_project(project.id)
    if existing:
        return [unpack_extras(slide) for slide in existing]

    slide_data: list[SlideData] = []
    for index, item in enumerate(outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        data = _slide_data_from_outline_item(item, index)
        if data is None:
            continue
        await _persist_outline_slide(repo, project.id, data)
        slide_data.append(data)
    return slide_data


async def apply_design_tokens(
    db: AsyncSession,
    project_id: str,
    slides: list[SlideData],
) -> None:
    """Apply the carousel design system before the design review gate."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None or not slides:
        return
    template = CarouselTemplateBuilder()
    run_design(project, slides, template=template)
    await repo.update_project(project)


async def generate_carousel_images(
    db: AsyncSession,
    ctx: CarouselImageGenerationContext,
) -> list[str]:
    """Generate hero images and return their filesystem paths."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(ctx.project_id))
    if project is None or not ctx.slides:
        return []
    output_dir = _carousel_output_dir(project.output_dir, ctx.project_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not project.output_dir:
        project.output_dir = str(output_dir)
        await repo.update_project(project)
    settings = get_settings()
    await run_images(
        ImageGenerationConfig(
            project=project,
            slides=ctx.slides,
            output_dir=output_dir,
            repo=repo,
            image_registry=ctx.image_registry,
            # AE-0121: editorial owns the workflow ``phase_progress`` write + SSE;
            # the presentation image node reports progress through this callback
            # instead of writing workflow state itself.
            progress_port=EditorialProgressReporter(repo, project),
            # AE-0208: inject the settings-backed provider-rate-limit controls
            # here (infrastructure-aware caller) so the image node stays free of
            # infrastructure imports.
            concurrency=settings.carousel_image_concurrency,
            max_attempts=settings.carousel_image_max_attempts,
        )
    )
    return await _collect_generated_image_paths(repo, project.id, output_dir)


async def _collect_generated_image_paths(
    repo: PostgresCarouselRepository,
    project_id: UUID,
    output_dir: Path,
) -> list[str]:
    refreshed = await repo.get_slides_by_project(project_id)
    asset_paths = [
        str(slide.image_path)
        for slide in refreshed
        if slide.image_path and str(slide.image_path).strip()
    ]
    if asset_paths:
        return asset_paths
    images_dir = output_dir / "images"
    if not images_dir.is_dir():
        return []
    return sorted(str(path) for path in images_dir.glob("slide_*.jpg"))


def _carousel_output_dir(output_dir: str | None, project_id: str) -> Path:
    if output_dir:
        return Path(output_dir).resolve()
    base_dir = Path(get_settings().carousel_output_dir).resolve()
    return base_dir / project_id


__all__ = [
    "CarouselImageGenerationContext",
    "apply_design_tokens",
    "ensure_slides_from_outline",
    "generate_carousel_images",
]
