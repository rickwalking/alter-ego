"""Map repaired localized slides to/from the ``carousel_slides`` projection.

The completed-project repair path reads its source of truth from the
persisted ``carousel_slides`` rows (authority rule: completed → projection
authoritative), reconstructs the canonical localized-slide records the
deterministic pipeline validates, then writes the repaired copy back through
the same ``_slide_data_from_draft`` + ``pack_extras`` mapping the content
pipeline uses — so a repaired projection is byte-identical to a freshly
persisted one.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    SLIDE_INDEX_KEY,
)
from rag_backend.application.services.carousel.editorial_distribution_slide import (
    SlideDataFromDraftInput,
    _slide_data_from_draft,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    STRUCTURED_EXTRA_KEYS,
    as_dict,
)
from rag_backend.application.services.carousel.types import pack_extras
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.domain.protocols.repositories import CarouselRepository

_SLIDE_TYPE_KEY = "slide_type"
_HEADING_KEY = "heading"
_BODY_KEY = "body"
_TRANSLATION_EN_KEY = "translation_en"


def _locale_payload(
    copy: tuple[str, str, str],
    structured_source: dict[str, object],
) -> dict[str, object]:
    """Build a canonical locale payload from ``(type, heading, body)`` + extras."""
    slide_type, heading, body = copy
    payload: dict[str, object] = {
        _SLIDE_TYPE_KEY: slide_type,
        _HEADING_KEY: heading,
        _BODY_KEY: body,
    }
    for key in STRUCTURED_EXTRA_KEYS:
        value = structured_source.get(key)
        if value is not None:
            payload[key] = value
    return payload


def _localized_record_from_slide(slide: CarouselSlide) -> dict[str, object]:
    """Reconstruct one canonical localized-slide record from a persisted row."""
    extras = slide.extras or {}
    translation_en = as_dict(extras.get(_TRANSLATION_EN_KEY)) or {}
    return {
        SLIDE_INDEX_KEY: slide.slide_number,
        _SLIDE_TYPE_KEY: slide.slide_type,
        PRESENTATION_PT_KEY: _locale_payload(
            (slide.slide_type, slide.heading, slide.body), dict(extras)
        ),
        PRESENTATION_EN_KEY: _locale_payload(
            (
                slide.slide_type,
                str(translation_en.get(_HEADING_KEY) or slide.heading),
                str(translation_en.get(_BODY_KEY) or slide.body),
            ),
            translation_en,
        ),
    }


def localized_from_slides(slides: list[CarouselSlide]) -> list[dict[str, object]]:
    """Build canonical localized-slide records from persisted projection rows."""
    return [_localized_record_from_slide(slide) for slide in slides]


def _apply_record_to_slide(slide: CarouselSlide, record: dict[str, object]) -> None:
    """Overwrite a projection row's copy from a repaired localized record."""
    slide_data = _slide_data_from_draft(
        SlideDataFromDraftInput(
            draft=record,
            slide_number=slide.slide_number,
            slide_type=slide.slide_type,
            translations_en={},
        )
    )
    slide.heading = slide_data.heading
    slide.body = slide_data.body
    slide.extras = pack_extras(slide_data)


async def apply_localized_to_slides(
    repo: CarouselRepository,
    slides: list[CarouselSlide],
    repaired_records: list[dict[str, object]],
) -> tuple[int, ...]:
    """Write repaired copy back to the matching projection rows by number."""
    records_by_number = {
        record.get(SLIDE_INDEX_KEY): record for record in repaired_records
    }
    updated: list[int] = []
    for slide in slides:
        record = records_by_number.get(slide.slide_number)
        if record is None:
            continue
        _apply_record_to_slide(slide, record)
        await repo.update_slide(slide)
        updated.append(slide.slide_number)
    return tuple(updated)


__all__ = [
    "apply_localized_to_slides",
    "localized_from_slides",
]
