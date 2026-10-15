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
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_draft,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_SLIDE_TYPE,
    canonical_slide_type,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.project_policy import project_policy
from rag_backend.application.services.carousel.slide_copy_casing import (
    repair_slide_data_casing,
)
from rag_backend.application.services.carousel.types import (
    MAX_SLIDES,
    SlideData,
    pack_extras,
)
from rag_backend.domain.constants.carousel import CAROUSEL_SLIDES_CONFIG_FORMAT
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
    policy: CarouselPresentationPolicy


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
        policy=_project_policy(project),
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
    slide_data = repair_slide_data_casing(slide_data, state.policy)
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
    state.project.slides_config = CAROUSEL_SLIDES_CONFIG_FORMAT.format(
        count=len(existing)
    )
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
    slide_data = repair_slide_data_casing(slide_data, state.policy)
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
    created = 0
    for index, item in enumerate(state.outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        await _create_slide_from_outline_item(state, index, item)
        created += 1
    # AE-0374: the real deck size (was always "7_slides"), read by design.py.
    state.project.slides_config = CAROUSEL_SLIDES_CONFIG_FORMAT.format(count=created)
    await state.repo.update_project(state.project)


def _project_policy(project: CarouselProject) -> CarouselPresentationPolicy:
    """AE-0374: the stamped contract sized to the project's deck."""
    return project_policy(project)


# Extras keys that carry visible copy (replaced, or dropped when the edited copy
# no longer has them); image_prompt / long_form_notes and any other extras are
# left untouched by a copy projection.
_COPY_EXTRAS_KEYS: tuple[str, ...] = (
    "features",
    "stats",
    "insight",
    "summary_points",
    "tldr_strip",
)
_TRANSLATION_EN_KEY = "translation_en"


def _merged_extras(
    current: dict[str, object] | None,
    slide_data: SlideData,
) -> dict[str, object] | None:
    extras = dict(current or {})
    fresh = pack_extras(slide_data) or {}
    for key in _COPY_EXTRAS_KEYS:
        if key in fresh:
            extras[key] = fresh[key]
        else:
            extras.pop(key, None)
    translation = fresh.get(_TRANSLATION_EN_KEY)
    if isinstance(translation, dict):
        previous = extras.get(_TRANSLATION_EN_KEY)
        base = dict(previous) if isinstance(previous, dict) else {}
        extras[_TRANSLATION_EN_KEY] = {**base, **translation}
    return extras or None


@dataclass(frozen=True)
class LocalizedCopyProjection:
    """Reviewer-edited localized slides to project onto the slide rows."""

    db: AsyncSession
    project_id: str
    localized_slides: list[dict[str, object]]


async def project_localized_copy_to_database(
    projection: LocalizedCopyProjection,
) -> tuple[int, ...]:
    """Write edited presentation copy onto existing slide rows (AE-0366).

    Only the visible copy changes: heading, body, the structured items and
    ``translation_en`` heading/body/items. The image path, image prompt,
    metadata and long-form notes are preserved, so no image is regenerated.
    """
    repo = PostgresCarouselRepository(session=projection.db)
    project = await repo.get_project_by_id(UUID(projection.project_id))
    if project is None:
        return ()
    policy = _project_policy(project)
    records = {
        record.get(SLIDE_INDEX_KEY): record
        for record in projection.localized_slides
        if as_dict(record.get(PRESENTATION_PT_KEY)) is not None
    }
    updated: list[int] = []
    for slide in await repo.get_slides_by_project(project.id):
        record = records.get(slide.slide_number)
        if record is None:
            continue
        slide_data = repair_slide_data_casing(
            _slide_data_from_draft(
                SlideDataFromDraftInput(
                    draft=dict(record),
                    slide_number=slide.slide_number,
                    slide_type=slide.slide_type,
                    translations_en={},
                ),
            ),
            policy,
        )
        slide.heading = slide_data.heading
        slide.body = slide_data.body
        slide.extras = _merged_extras(slide.extras, slide_data)
        await repo.update_slide(slide)
        updated.append(slide.slide_number)
    return tuple(updated)


__all__ = [
    "LocalizedCopyProjection",
    "SlideDraftsContext",
    "apply_slide_drafts_to_database",
    "project_localized_copy_to_database",
]
