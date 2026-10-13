"""Small JSON and text coercions for untrusted collector payloads.

``json.loads`` is cast to ``object`` at this boundary so callers never
see an explicit ``Any``.
"""

from __future__ import annotations

import json
from typing import cast


def loads_json(text: str) -> object | None:
    """Parse JSON text, or None when it is not valid JSON."""
    try:
        return cast(object, json.loads(text))
    except json.JSONDecodeError:
        return None


def as_mapping(value: object) -> dict[str, object] | None:
    """Return a string-keyed object dict, or None."""
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def as_list(value: object) -> list[object]:
    """Return a list, or an empty list when ``value`` is not one."""
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def as_str(value: object) -> str:
    """Return a stripped string, or ``""`` for every other type."""
    if isinstance(value, str):
        return value.strip()
    return ""


def as_int(value: object) -> int | None:
    """Return an int. Booleans are not ints here."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
