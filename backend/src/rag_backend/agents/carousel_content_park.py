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

from collections.abc import Mapping

import structlog

from rag_backend.agents.harness.interrupts import iter_interrupt_values
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
    PHASE_CONTENT,
    PHASE_STATUS_APPROVED,
    SEND_BACK_TARGET_PHASE_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    LOG_CONTENT_MANUAL_FIXES_KEPT,
    PAYLOAD_KEY_PARKED_ARTIFACTS,
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_LOCALIZED_SLIDES,
    STATE_FIELD_PHASE_FEEDBACK,
    STATE_FIELD_PHASE_STATUS,
    STATE_FIELD_PROJECT_ID,
)

logger = structlog.get_logger()

_FIELD_CONTENT_APPROVED = "content_approved"
_FIELD_CURRENT_PHASE = "current_phase"
_PAYLOAD_TYPE_KEY = "type"


def parked_content_updates(snapshot: object) -> dict[str, object] | None:
    """Checkpoint updates for a content review parked with unsaved artifacts.

    ``None`` when the graph is not parked at the content review, the payload
    carries no artifacts (legacy interrupt, or a replay that reused them) or
    they are already saved. ``content_approved`` is reset: the review is still
    pending, and a stale True (final-review send-back) would route the write
    past the content gate. ``current_phase`` is pinned to content (AE-0413):
    the interrupted node never committed it, so the checkpoint still said
    ``outline`` on the first content gate.
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
                _FIELD_CURRENT_PHASE: PHASE_CONTENT,
            }
    return None


def _is_manual_fixes_revise(
    review_update: Mapping[str, object],
    state: Mapping[str, object],
) -> bool:
    """True for a revise that only carried reviewer slide edits (AE-0413).

    The review update already applied and re-validated the edits
    (``localized_slides`` is only in it when edits were applied). With no
    send-back and no new content note there is nothing to regenerate.
    """
    if review_update.get(STATE_FIELD_PHASE_STATUS) == PHASE_STATUS_APPROVED:
        return False
    if STATE_FIELD_LOCALIZED_SLIDES not in review_update:
        return False
    if review_update.get(SEND_BACK_TARGET_PHASE_KEY):
        return False
    return not _has_active_content_note(state)


def _has_active_content_note(state: Mapping[str, object]) -> bool:
    """A content note no regeneration has used yet (AE-0405 ``phase_feedback``)."""
    notes = state.get(STATE_FIELD_PHASE_FEEDBACK)
    if not isinstance(notes, Mapping):
        return False
    content = notes.get(PHASE_CONTENT)
    if not isinstance(content, list):
        return False
    return any(str(note).strip() for note in content)


def manual_fixes_park_updates(
    review_update: Mapping[str, object],
    state: Mapping[str, object],
) -> dict[str, object]:
    """Keep hand-fixed copy as the parked artifacts of the next entry (AE-0413).

    "Submit manual fixes" (a revise carrying only ``edited_localized_slides``)
    re-entered the content node, whose ensure rebuilt every localized slide
    from the PT drafts (the EN copy fell back to Portuguese, structured items
    were dropped) and re-drafted the blocking slides with the LLM. With the
    parked marker set, the next entry reuses the edited, re-validated copy:
    no regeneration, no translation, no LLM call.
    """
    if not _is_manual_fixes_revise(review_update, state):
        return {}
    logger.info(
        LOG_CONTENT_MANUAL_FIXES_KEPT,
        project_id=str(state.get(STATE_FIELD_PROJECT_ID, "")),
    )
    return {STATE_FIELD_CONTENT_ARTIFACTS_PARKED: True}


__all__ = ["manual_fixes_park_updates", "parked_content_updates"]
