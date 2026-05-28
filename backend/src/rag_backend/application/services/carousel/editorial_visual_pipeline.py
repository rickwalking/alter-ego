"""Design and image generation helpers for the editorial workflow."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.images import run_images
from rag_backend.application.services.carousel.types import SlideData, unpack_extras
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import (
    ImageProviderRegistry,
)
from rag_backend.domain.constants.carousel import SLIDE_TYPE_CONTENT, SLIDE_TYPE_INTRO
from rag_backend.domain.models import CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)

DEFAULT_OUTPUT_BASE = "./output/carousels"


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
    for index, item in enumerate(outline):
        if not isinstance(item, dict):
            continue
        slide_number = int(item.get("slide_index", index + 1))
        heading = str(item.get("title", ""))
        key_points = item.get("key_points", [])
        body_parts = [
            str(point) for point in key_points if isinstance(point, (str, int, float))
        ]
        body = " · ".join(body_parts) if body_parts else heading
        slide_type = SLIDE_TYPE_INTRO if slide_number == 1 else SLIDE_TYPE_CONTENT
        image_prompt = f"Editorial illustration for carousel slide: {heading}"
        data = SlideData(
            slide_number=slide_number,
            slide_type=slide_type,
            heading=heading,
            body=body,
            image_prompt=image_prompt,
        )
        slide = CarouselSlide(
            project_id=project.id,
            slide_number=data.slide_number,
            slide_type=data.slide_type,
            heading=data.heading,
            body=data.body,
            image_prompt=data.image_prompt,
        )
        await repo.create_slide(slide)
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
    project_id: str,
    slides: list[SlideData],
    image_registry: ImageProviderRegistry,
) -> list[str]:
    """Generate hero images and return their filesystem paths."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None or not slides:
        return []
    output_dir = Path(project.output_dir or f"{DEFAULT_OUTPUT_BASE}/{project_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    await run_images(
        project,
        slides,
        output_dir,
        repo=repo,
        image_registry=image_registry,
    )
    refreshed = await repo.get_slides_by_project(project.id)
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


__all__ = [
    "apply_design_tokens",
    "ensure_slides_from_outline",
    "generate_carousel_images",
]
