"""Emphasis in each locale's own convention before the shorten step measures copy.

The convention: PT copy marks emphasis ``**...**``, EN copy ``<strong>...</strong>``.
A bilingual draft blob carries EN copy the drafting model wrote with the PT
markers, so its emphasis is a blocking ``emphasis_markup_locale_mismatch``, and
the EN tags are 13 characters longer than the PT markers. The bounded review
repair converts the markers only when the whole payload then validates, so on a
payload that still has a length blocker (or that the longer tags push over a
budget) the conversion is discarded and every emphasized EN field stays blocked.

The shorten step therefore converts balanced emphasis first, deterministically
(``normalize_emphasis``, the conversion the review repair applies), and measures
every field as it will render: an EN field the tags push over its budget becomes
a shorten target like any other. Answers get the same conversion before they
are checked. Empty or unbalanced markers are left for the validator; the owner's
hook heading (an excluded address) is never touched.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    text_at,
    visible_paths,
    with_text,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    normalize_emphasis,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.workflow_state_fields import STATE_FIELD_SLIDE_INDEX

_LOCALE_KEYS: tuple[tuple[str, str], ...] = (
    (LANGUAGE_PT, PRESENTATION_PT_KEY),
    (LANGUAGE_EN, PRESENTATION_EN_KEY),
)


@dataclass(frozen=True)
class EmphasisScope:
    """Which slides the conversion may touch and which fields it must leave alone.

    ``only_slides`` None means every slide; ``excluded`` holds
    ``(slide, locale, field)`` addresses that are never rewritten.
    """

    only_slides: frozenset[int] | None = None
    excluded: frozenset[tuple[int, str, str]] = frozenset()


def _converted(
    payload: dict[str, object], address: tuple[int, str], scope: EmphasisScope
) -> dict[str, object]:
    index, locale = address
    updated = payload
    for path in visible_paths(payload):
        text = text_at(updated, path)
        if not text or (index, locale, path) in scope.excluded:
            continue
        converted = normalize_emphasis(locale, text)
        if converted != text:
            updated = with_text(updated, path, converted)
    return updated


def _slide_in_convention(
    slide: dict[str, object], scope: EmphasisScope
) -> dict[str, object]:
    index = slide.get(STATE_FIELD_SLIDE_INDEX)
    if not isinstance(index, int):
        return slide
    if scope.only_slides is not None and index not in scope.only_slides:
        return slide
    updated = dict(slide)
    for locale, key in _LOCALE_KEYS:
        payload = as_dict(slide.get(key))
        if payload is not None:
            updated[key] = _converted(payload, (index, locale), scope)
    return updated


def slides_in_locale_emphasis(
    slides: list[dict[str, object]], scope: EmphasisScope
) -> list[dict[str, object]]:
    """The slides with every balanced emphasis pair in its locale's convention."""
    return [_slide_in_convention(slide, scope) for slide in slides]


def answer_in_locale_emphasis(locale: str, text: str) -> str:
    """A model answer with its balanced emphasis in the field's convention."""
    return normalize_emphasis(locale, text)


__all__ = [
    "EmphasisScope",
    "answer_in_locale_emphasis",
    "slides_in_locale_emphasis",
]
