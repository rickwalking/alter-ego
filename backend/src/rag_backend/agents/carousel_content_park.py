"""Durable content-review artifacts (AE-0405).

The content node runs its ensure (which may regenerate every slide with the
LLM) BEFORE its review interrupt, and LangGraph replays the whole node on
resume. An interrupted node's return value is never committed, so without this
the replay regenerated again with the same notes and committed drafts nobody
reviewed (carousel 98a2e2f0: hand-fixed slides 3 and 8 replaced on approval).

The node puts that pass's artifact updates on the interrupt payload; once the
graph parks, the engine writes them to the checkpoint with the parked marker
and re-parks, so the replay on resume reuses them.
"""

from __future__ import annotations

from rag_backend.agents.harness.interrupts import iter_interrupt_values
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
)
from rag_backend.domain.constants.content_feedback import (
    PAYLOAD_KEY_PARKED_ARTIFACTS,
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
)

_FIELD_CONTENT_APPROVED = "content_approved"
_PAYLOAD_TYPE_KEY = "type"


def parked_content_updates(snapshot: object) -> dict[str, object] | None:
    """Checkpoint updates for a content review parked with unsaved artifacts.

    ``None`` when the graph is not parked at the content review, the payload
    carries no artifacts (legacy interrupt, or a replay that reused them) or
    they are already saved. ``content_approved`` is reset: the review is still
    pending, and a stale True (final-review send-back) would route the write
    past the content gate.
    """
    values = getattr(snapshot, "values", None)
    if not isinstance(values, dict):
        return None
    if values.get(STATE_FIELD_CONTENT_ARTIFACTS_PARKED) is True:
        return None
    for payload in iter_interrupt_values(snapshot):
        if payload.get(_PAYLOAD_TYPE_KEY) != INTERRUPT_TYPE_CONTENT_REVIEW:
            continue
        artifacts = payload.get(PAYLOAD_KEY_PARKED_ARTIFACTS)
        if isinstance(artifacts, dict) and artifacts:
            return {
                **artifacts,
                STATE_FIELD_CONTENT_ARTIFACTS_PARKED: True,
                _FIELD_CONTENT_APPROVED: False,
            }
    return None


__all__ = ["parked_content_updates"]
