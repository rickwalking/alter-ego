"""Read the durable transport priority without trusting malformed JSON."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.modules.generation_queue.constants import (
    ORDINARY_PRIORITY,
    PAYLOAD_MANUAL_PRIORITY,
)


def priority_of(payload: Mapping[str, object]) -> int:
    """Return an integer manual priority, or ordinary priority for other values."""
    value = payload.get(PAYLOAD_MANUAL_PRIORITY, ORDINARY_PRIORITY)
    if isinstance(value, bool) or not isinstance(value, int):
        return ORDINARY_PRIORITY
    return value


__all__ = ["priority_of"]
