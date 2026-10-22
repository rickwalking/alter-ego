"""Typed readers for loosely typed workflow-state values."""

from __future__ import annotations

from collections.abc import Mapping


def strings_of(value: object) -> tuple[str, ...]:
    """The stripped non-empty strings of a list value; anything else yields ``()``."""
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def mappings_at(
    state: Mapping[str, object] | None, key: str
) -> list[Mapping[str, object]]:
    """The mapping items of ``state[key]``; a missing state or non-list yields ``[]``."""
    raw = state.get(key) if state is not None else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]
