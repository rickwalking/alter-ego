"""SSE formatting for editorial workflow."""

from __future__ import annotations

import json

from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    SSE_EVENT_PHASE_CHANGE,
    SSE_PAYLOAD_FIELD_EVENT,
)


def format_sse_event(
    payload: dict[str, object],
    *,
    event_id: int | None = None,
) -> str:
    """Format a workflow update dict as an SSE frame."""
    event_type = str(payload.get(SSE_PAYLOAD_FIELD_EVENT, SSE_EVENT_PHASE_CHANGE))
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(payload, default=str)}")
    return "\n".join(lines) + "\n\n"


__all__ = [
    "format_sse_event",
]
