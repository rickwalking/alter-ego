"""A model rewrite clears the casing markers it supersedes.

The sentence-case repair marks every field it had to capitalize, and the
marker blocks the gate until the copy is regenerated or edited. An owner edit
drops a locale's markers; the model fix deep-copied them, so prod slide 8 of
be190a0c (markers only) could never be fixed. A field's marker is now dropped
when the model's answer set that field and the model's own text passes the
live sentence-case check (before the deterministic repair, which would
capitalize a lowercase answer and hide it).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.draft_blob_text import (
    parse_object_text,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
    as_dict,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    ITEM_LISTS,
    text_at,
)
from rag_backend.application.services.carousel.presentation_casing import (
    sentence_case_findings,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    CASING_MARKER_FIELD,
    CASING_MARKER_LOCALE,
    CASING_REPAIRS_KEY,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT

_COPY_KEYS = ("heading", "body")
_ITEM_KEYS = ("title", "body")
_PAYLOAD_KEYS: dict[str, str] = {
    LANGUAGE_PT: PRESENTATION_PT_KEY,
    LANGUAGE_EN: PRESENTATION_EN_KEY,
}


@dataclass(frozen=True)
class MarkerClear:
    """The model's raw answer and the policy whose casing rules apply."""

    answer: str
    policy: CarouselPresentationPolicy


def _item_texts(list_field: str, items: object) -> dict[str, str]:
    if not isinstance(items, list):
        return {}
    return {
        f"{list_field}[{index}].{key}": value
        for index, item in enumerate(items)
        if isinstance(item, Mapping)
        for key in _ITEM_KEYS
        if isinstance(value := item.get(key), str) and value.strip()
    }


def _answered(locale_answer: Mapping[str, object]) -> dict[str, str]:
    """The texts one locale answer sets, by validator path, as merged."""
    texts = {
        key: value.strip()
        for key in _COPY_KEYS
        if isinstance(value := locale_answer.get(key), str)
    }
    for list_field in ITEM_LISTS:
        texts.update(_item_texts(list_field, locale_answer.get(list_field)))
    return texts


def _cleared_fields(
    record: Mapping[str, object], clear: MarkerClear
) -> set[tuple[str, str]]:
    parsed = parse_object_text(clear.answer) or {}
    cleared: set[tuple[str, str]] = set()
    for locale, payload_key in _PAYLOAD_KEYS.items():
        locale_answer = parsed.get(locale)
        payload = as_dict(record.get(payload_key))
        if not isinstance(locale_answer, Mapping) or payload is None:
            continue
        failing = {
            f.field for f in sentence_case_findings(payload, locale, clear.policy)
        }
        cleared.update(
            (locale, path)
            for path, text in _answered(locale_answer).items()
            if path not in failing and text_at(payload, path) == text
        )
    return cleared


def clear_rewritten_casing_markers(
    record: dict[str, object], clear: MarkerClear
) -> dict[str, object]:
    """``record`` without the markers of the fields the model rewrote correctly."""
    raw = record.get(CASING_REPAIRS_KEY)
    if not isinstance(raw, list) or not raw:
        return record
    cleared = _cleared_fields(record, clear)
    kept = [
        marker
        for marker in raw
        if not isinstance(marker, Mapping)
        or (marker.get(CASING_MARKER_LOCALE), marker.get(CASING_MARKER_FIELD))
        not in cleared
    ]
    updated = dict(record)
    if kept:
        updated[CASING_REPAIRS_KEY] = kept
    else:
        updated.pop(CASING_REPAIRS_KEY, None)
    return updated


__all__ = ["MarkerClear", "clear_rewritten_casing_markers"]
