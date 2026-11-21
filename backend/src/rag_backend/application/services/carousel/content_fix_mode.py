"""Fix the blocked fields instead of re-drafting the deck.

A content revision is either a rework or a fix:

- a **rework** re-drafts the slides: the owner wrote a note ("make it
  shorter", "slide 3 needs a number"), so new content is the point;
- a **fix** keeps every slide as stored and rewrites only the fields the
  content gate blocks, through the targeted field repair. It applies when the
  gate is blocking and every active note is system-written (an owner Retry or
  an autopilot rework of a blocked phase).

Prod carousel 4223b53a: three Retries of a gate that blocked only slide 8's
summary bodies each re-drafted all 9 slides from a note that named no slide.
Every redraft brought new violations elsewhere and the persona score fell from
77 to 30, so the gate never cleared.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.application.services.carousel.content_feedback_lifecycle import (
    active_note_sources,
)
from rag_backend.application.services.carousel.revision_scope import blocked_slides
from rag_backend.domain.constants.carousel_workflow import PHASE_CONTENT
from rag_backend.domain.constants.content_feedback import FEEDBACK_SOURCE_AUTOPILOT
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_LOCALIZED_SLIDES,
    STATE_FIELD_SLIDE_DRAFTS,
)


def _has_list(state: Mapping[str, object], key: str) -> bool:
    value = state.get(key)
    return isinstance(value, list) and bool(value)


def is_fix_revision(state: Mapping[str, object]) -> bool:
    """True when this content revision fixes the blocked fields only."""
    sources = active_note_sources(state, PHASE_CONTENT)
    if not sources or any(source != FEEDBACK_SOURCE_AUTOPILOT for source in sources):
        return False
    if not _has_list(state, STATE_FIELD_LOCALIZED_SLIDES):
        return False
    if not _has_list(state, STATE_FIELD_SLIDE_DRAFTS):
        return False
    return bool(blocked_slides(state))


__all__ = ["is_fix_revision"]
