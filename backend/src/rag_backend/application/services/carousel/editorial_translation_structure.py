"""The structured fields the EN translation carries.

The localized builder copies a draft's top-level structured extras
(``tldr_strip``, item lists, ``content_kind`` ...) into the PT payload, and the
same keys from the EN translation into the EN payload. The translator used to
send and keep only ``heading``/``body``, so an intro with a PT TL;DR always
came back ``intro:plain`` in EN (``translation_shape_mismatch``, prod 5344b6c6)
and the owner could not fix it.

Now the translation request carries the draft's ``tldr_strip`` and item texts,
and the parsed translation gets the same structure: translated texts where the
model answered with the same shape. An unanswered TL;DR stays absent (the gate
blocks on the shape mismatch and its repair fills and translates it); an item
list with another shape keeps the PT items, which the language checks flag.
Non-text extras are copied.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping

from rag_backend.application.services.carousel.localized_slide_builder import (
    STRUCTURED_EXTRA_KEYS,
)
from rag_backend.application.services.carousel.owner_autofix_paths import ITEM_LISTS

TLDR_STRIP_KEY = "tldr_strip"
_ITEM_TEXT_KEYS: tuple[str, ...] = ("title", "body")


def _item_texts(items: object) -> list[dict[str, str]] | None:
    if not isinstance(items, list) or not items:
        return None
    return [
        {key: str(item.get(key) or "") for key in _ITEM_TEXT_KEYS}
        for item in items
        if isinstance(item, Mapping)
    ] or None


def structured_source(draft: Mapping[str, object]) -> dict[str, object]:
    """The PT structured texts of a draft, as the translator should see them."""
    source: dict[str, object] = {}
    tldr = draft.get(TLDR_STRIP_KEY)
    if isinstance(tldr, str) and tldr.strip():
        source[TLDR_STRIP_KEY] = tldr
    for list_field in ITEM_LISTS:
        texts = _item_texts(draft.get(list_field))
        if texts is not None:
            source[list_field] = texts
    return source


def _translated_items(pt_items: list[object], answered: object) -> list[object]:
    """PT items with the answered EN texts, by position; PT when shapes differ."""
    merged = copy.deepcopy(pt_items)
    if not isinstance(answered, list) or len(answered) != len(pt_items):
        return merged
    for item, answer in zip(merged, answered, strict=True):
        if not isinstance(item, dict) or not isinstance(answer, Mapping):
            continue
        for key in _ITEM_TEXT_KEYS:
            text = answer.get(key)
            if isinstance(text, str) and text.strip():
                item[key] = text.strip()
    return merged


def _translated_value(
    key: str, pt_value: object, answer: Mapping[str, object]
) -> object | None:
    """The EN value of one extra; None when it must stay absent.

    An unanswered TL;DR is never filled with the PT text: EN stays without one,
    so ``translation_shape_mismatch`` keeps the slide blocked and the gate
    repair fills it from PT and translates it (a PT TL;DR must not ship as EN).
    """
    answered = answer.get(key)
    if key == TLDR_STRIP_KEY:
        return (
            answered.strip() if isinstance(answered, str) and answered.strip() else None
        )
    if key in ITEM_LISTS and isinstance(pt_value, list):
        return _translated_items(pt_value, answered)
    return copy.deepcopy(pt_value)


def structured_translation(
    draft: Mapping[str, object],
    answer: Mapping[str, object],
) -> dict[str, object]:
    """The EN structured extras: the PT draft's keys, translated where possible."""
    structured: dict[str, object] = {}
    for key in STRUCTURED_EXTRA_KEYS:
        pt_value = draft.get(key)
        if pt_value is None:
            continue
        value = _translated_value(key, pt_value, answer)
        if value is not None:
            structured[key] = value
    return structured


__all__ = [
    "TLDR_STRIP_KEY",
    "structured_source",
    "structured_translation",
]
