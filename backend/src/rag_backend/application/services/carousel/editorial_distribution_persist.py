"""Database persistence for editorial distribution."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_slide import (
    SlideDataFromDraftInput,
    _slide_data_from_draft,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_SLIDE_TYPE,
    canonical_slide_type,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES, pack_extras
from rag_backend.domain.constants.carousel import CAROUSEL_SLIDES_CONFIG_SEVEN
from rag_backend.domain.models import CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)


@dataclass(frozen=True)
class SlideDraftsContext:
    """Input bundle for applying slide drafts to the database."""

    db: AsyncSession
    project_id: str
    outline: list[dict[str, object]]
    slide_drafts: list[dict[str, object]]
    translations_en: dict[int, dict[str, object]]


async def apply_slide_drafts_to_database(
    context: SlideDraftsContext,
) -> None:
    """Merge outline + drafts (+ EN) into persisted carousel slides."""
    repo = PostgresCarouselRepository(session=context.db)
    project = await repo.get_project_by_id(UUID(context.project_id))
    if project is None:
        return

    drafts_by_index: dict[int, dict[str, object]] = {}
    for draft in context.slide_drafts:
        if isinstance(draft, dict):
            drafts_by_index[int(draft.get(SLIDE_INDEX_KEY, 0))] = normalize_slide_draft(
                draft
            )

    existing = await repo.get_slides_by_project(project.id)
    if existing:
        for slide in existing:
            draft = drafts_by_index.get(slide.slide_number)
            if draft is None:
                continue
            slide_data = _slide_data_from_draft(
                SlideDataFromDraftInput(
                    draft=draft,
                    slide_number=slide.slide_number,
                    slide_type=slide.slide_type,
                    translations_en=context.translations_en,
                ),
            )
            slide.heading = slide_data.heading
            slide.body = slide_data.body
            slide.image_prompt = slide_data.image_prompt or ""
            slide.extras = pack_extras(slide_data)
            slide.metadata = {}
            slide.image_path = None
            await repo.update_slide(slide)
        project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
        await repo.update_project(project)
        return

    for index, item in enumerate(context.outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        slide_number = int(item.get(OUTLINE_FIELD_SLIDE_INDEX, index + 1))
        draft = drafts_by_index.get(slide_number, item)
        slide_type = str(
            item.get(OUTLINE_FIELD_SLIDE_TYPE, "") or canonical_slide_type(slide_number)
        )
        slide_data = _slide_data_from_draft(
            SlideDataFromDraftInput(
                draft=draft,
                slide_number=slide_number,
                slide_type=slide_type,
                translations_en=context.translations_en,
            ),
        )
        await repo.create_slide(
            CarouselSlide(
                project_id=project.id,
                slide_number=slide_number,
                slide_type=slide_type,
                heading=slide_data.heading,
                body=slide_data.body,
                image_prompt=slide_data.image_prompt or "",
                extras=pack_extras(slide_data),
            )
        )
    project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
    await repo.update_project(project)


__all__ = [
    "SlideDraftsContext",
    "apply_slide_drafts_to_database",
]
