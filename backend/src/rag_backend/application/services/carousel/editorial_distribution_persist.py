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
from rag_backend.domain.models import CarouselProject, CarouselSlide
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


@dataclass(frozen=True)
class _SlideDraftsState:
    """Internal shared state for slide draft operations."""

    repo: PostgresCarouselRepository
    project: CarouselProject
    drafts_by_index: dict[int, dict[str, object]]
    translations_en: dict[int, dict[str, object]]
    outline: list[dict[str, object]]


def _build_drafts_by_index(
    slide_drafts: list[dict[str, object]],
) -> dict[int, dict[str, object]]:
    """Normalise slide drafts and index them by slide number."""
    drafts_by_index: dict[int, dict[str, object]] = {}
    for draft in slide_drafts:
        if isinstance(draft, dict):
            drafts_by_index[int(draft.get(SLIDE_INDEX_KEY, 0))] = normalize_slide_draft(
                draft
            )
    return drafts_by_index


async def apply_slide_drafts_to_database(
    context: SlideDraftsContext,
) -> None:
    """Merge outline + drafts (+ EN) into persisted carousel slides.

    Dispatches to update or create path based on whether slides already exist.
    """
    repo = PostgresCarouselRepository(session=context.db)
    project = await repo.get_project_by_id(UUID(context.project_id))
    if project is None:
        return

    drafts_by_index = _build_drafts_by_index(context.slide_drafts)
    state = _SlideDraftsState(
        repo=repo,
        project=project,
        drafts_by_index=drafts_by_index,
        translations_en=context.translations_en,
        outline=context.outline,
    )

    existing = await repo.get_slides_by_project(project.id)
    if existing:
        await _update_existing_slides(state, existing)
    else:
        await _create_new_slides(state)


async def _apply_draft_to_existing_slide(
    state: _SlideDraftsState,
    slide: CarouselSlide,
    draft: dict[str, object],
) -> None:
    """Apply a single draft payload to an existing CarouselSlide row."""
    slide_data = _slide_data_from_draft(
        SlideDataFromDraftInput(
            draft=draft,
            slide_number=slide.slide_number,
            slide_type=slide.slide_type,
            translations_en=state.translations_en,
        ),
    )
    slide.heading = slide_data.heading
    slide.body = slide_data.body
    slide.image_prompt = slide_data.image_prompt or ""
    slide.extras = pack_extras(slide_data)
    slide.metadata = {}
    slide.image_path = None
    await state.repo.update_slide(slide)


async def _update_existing_slides(
    state: _SlideDraftsState,
    existing: list[CarouselSlide],
) -> None:
    """Update existing slides with new draft data."""
    for slide in existing:
        draft = state.drafts_by_index.get(slide.slide_number)
        if draft is None:
            continue
        await _apply_draft_to_existing_slide(state, slide, draft)
    state.project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
    await state.repo.update_project(state.project)


async def _create_slide_from_outline_item(
    state: _SlideDraftsState,
    index: int,
    item: dict[str, object],
) -> None:
    """Create a single CarouselSlide row from an outline item with optional draft overlay."""
    slide_number = int(item.get(OUTLINE_FIELD_SLIDE_INDEX, index + 1))
    draft = state.drafts_by_index.get(slide_number, item)
    slide_type = str(
        item.get(OUTLINE_FIELD_SLIDE_TYPE, "") or canonical_slide_type(slide_number)
    )
    slide_data = _slide_data_from_draft(
        SlideDataFromDraftInput(
            draft=draft,
            slide_number=slide_number,
            slide_type=slide_type,
            translations_en=state.translations_en,
        ),
    )
    await state.repo.create_slide(
        CarouselSlide(
            project_id=state.project.id,
            slide_number=slide_number,
            slide_type=slide_type,
            heading=slide_data.heading,
            body=slide_data.body,
            image_prompt=slide_data.image_prompt or "",
            extras=pack_extras(slide_data),
        )
    )


async def _create_new_slides(
    state: _SlideDraftsState,
) -> None:
    """Create new slides from draft data and outline."""
    for index, item in enumerate(state.outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        await _create_slide_from_outline_item(state, index, item)
    state.project.slides_config = CAROUSEL_SLIDES_CONFIG_SEVEN
    await state.repo.update_project(state.project)


__all__ = [
    "SlideDraftsContext",
    "apply_slide_drafts_to_database",
]
