"""Normalize editorial outlines to the canonical seven-slide carousel contract."""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    OUTLINE_LEGACY_HEADING_KEY,
)
from rag_backend.application.services.carousel.types import MAX_SLIDES
from rag_backend.application.services.carousel.visible_copy_sanitize import (
    sanitize_visible_copy,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_PT,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)

OUTLINE_FIELD_SLIDE_INDEX = "slide_index"
OUTLINE_FIELD_TITLE = "title"
OUTLINE_FIELD_KEY_POINTS = "key_points"
OUTLINE_FIELD_SLIDE_TYPE = "slide_type"
OUTLINE_FIELD_TLDR = "tldr_strip"

_CANONICAL_SLIDE_TYPES: tuple[str, ...] = (
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CTA,
)


def canonical_slide_type(slide_number: int) -> str:
    """Return the expected slide type for a 1-based slide index (1..7)."""
    if slide_number < 1:
        return SLIDE_TYPE_CONTENT
    index = min(slide_number, len(_CANONICAL_SLIDE_TYPES)) - 1
    return _CANONICAL_SLIDE_TYPES[index]


def normalize_editorial_outline(
    raw_outline: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Trim to MAX_SLIDES, renumber indices, and assign canonical slide types."""
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(raw_outline[:MAX_SLIDES]):
        if not isinstance(item, dict):
            continue
        slide_number = index + 1
        title = sanitize_visible_copy(
            item.get(OUTLINE_FIELD_TITLE, "")
            or item.get(OUTLINE_LEGACY_HEADING_KEY, ""),
            locale=LANGUAGE_PT,
        )
        raw_points = item.get(OUTLINE_FIELD_KEY_POINTS, [])
        key_points: list[str] = []
        if isinstance(raw_points, list):
            for point in raw_points:
                cleaned = sanitize_visible_copy(point, locale=LANGUAGE_PT)
                if cleaned:
                    key_points.append(cleaned)
        slide: dict[str, object] = {
            OUTLINE_FIELD_SLIDE_INDEX: slide_number,
            OUTLINE_FIELD_TITLE: title,
            OUTLINE_FIELD_KEY_POINTS: key_points,
            OUTLINE_FIELD_SLIDE_TYPE: canonical_slide_type(slide_number),
        }
        tldr = item.get(OUTLINE_FIELD_TLDR)
        if slide_number == 1:
            cleaned_tldr = sanitize_visible_copy(tldr, locale=LANGUAGE_PT)
            if cleaned_tldr:
                slide[OUTLINE_FIELD_TLDR] = cleaned_tldr
        normalized.append(slide)
    return normalized


__all__ = [
    "canonical_slide_type",
    "normalize_editorial_outline",
]
