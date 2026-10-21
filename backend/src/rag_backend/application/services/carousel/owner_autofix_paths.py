"""Read and write the visible texts of one locale payload by path.

Paths match the presentation validator's ``field`` values: ``heading``,
``body``, ``tldr_strip`` and ``<list>[<n>].title`` / ``<list>[<n>].body`` for
the structured items (features, summary points, closing actions).
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Mapping

_HEADING = "heading"
_BODY = "body"
_TLDR = "tldr_strip"
_ITEM_KEYS = ("title", "body")
ITEM_LISTS: tuple[str, ...] = ("features", "summary_points", "actions")
_ITEM_PATH = re.compile(r"^(\w+)\[(\d+)\]\.(\w+)$")


def items_of(
    payload: Mapping[str, object], list_field: str
) -> list[Mapping[str, object]]:
    """The mapping items of one structured list (others are skipped)."""
    raw = payload.get(list_field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def complete_items(payload: Mapping[str, object], list_field: str) -> int:
    """How many items of a list have both a title and a body."""
    return sum(
        1
        for item in items_of(payload, list_field)
        if str(item.get("title") or "").strip() and str(item.get("body") or "").strip()
    )


def visible_paths(payload: Mapping[str, object]) -> list[str]:
    """Every path of a rendered text in the payload."""
    paths = [_HEADING, _BODY, _TLDR]
    for list_field in ITEM_LISTS:
        raw = payload.get(list_field)
        if not isinstance(raw, list):
            continue
        for index, item in enumerate(raw):
            if isinstance(item, Mapping):
                paths.extend(f"{list_field}[{index}].{key}" for key in _ITEM_KEYS)
    return paths


def text_at(payload: Mapping[str, object], path: str) -> str:
    """The text at a path, or "" when absent or not a string."""
    match = _ITEM_PATH.match(path)
    if match is None:
        value = payload.get(path)
        return value if isinstance(value, str) else ""
    raw = payload.get(match.group(1))
    index = int(match.group(2))
    if not isinstance(raw, list) or index >= len(raw):
        return ""
    item = raw[index]
    value = item.get(match.group(3)) if isinstance(item, Mapping) else None
    return value if isinstance(value, str) else ""


def with_text(payload: Mapping[str, object], path: str, text: str) -> dict[str, object]:
    """A copy of the payload with the text at an existing path replaced."""
    updated = copy.deepcopy(dict(payload))
    match = _ITEM_PATH.match(path)
    if match is None:
        if isinstance(updated.get(path), str):
            updated[path] = text
        return updated
    raw = updated.get(match.group(1))
    index = int(match.group(2))
    if isinstance(raw, list) and index < len(raw) and isinstance(raw[index], dict):
        raw[index][match.group(3)] = text
    return updated


def map_texts(
    payload: Mapping[str, object],
    transform: Callable[[str], str],
) -> dict[str, object]:
    """A copy of the payload with every non-empty visible text transformed."""
    updated = copy.deepcopy(dict(payload))
    for path in visible_paths(updated):
        text = text_at(updated, path)
        if text:
            updated = with_text(updated, path, transform(text))
    return updated


__all__ = [
    "ITEM_LISTS",
    "complete_items",
    "items_of",
    "map_texts",
    "text_at",
    "visible_paths",
    "with_text",
]
