"""Read the escalation detail off a state-changed event."""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.modules.autopilot.constants import PAYLOAD_DETAIL


def detail_of(payload: Mapping[str, object]) -> str:
    """Escalation detail copied onto the state-changed event, or empty."""
    value = payload.get(PAYLOAD_DETAIL)
    return value if isinstance(value, str) else ""


__all__ = ["detail_of"]
