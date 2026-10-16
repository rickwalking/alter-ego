"""Reviewer feedback-note lifecycle (AE-0405).

A revision note steers the ONE regeneration that uses it. ``phase_feedback``
keeps the active note texts (shape unchanged for the API); the tagged entries
(source + timestamp) live in ``phase_feedback_notes`` and every consumed note
moves to ``phase_feedback_history`` with its status:

- ``applied``: a content regeneration used it;
- ``dropped``: an autopilot note whose content gate passed without it;
- ``migrated``: a legacy untagged note that predates the last regeneration.

Pure functions over the workflow state; each returns the state updates to write.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

import structlog

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_ENTRY_ADDED_AT,
    FEEDBACK_ENTRY_NOTE,
    FEEDBACK_ENTRY_SETTLED_AT,
    FEEDBACK_ENTRY_SOURCE,
    FEEDBACK_ENTRY_STATUS,
    FEEDBACK_SOURCE_AUTOPILOT,
    FEEDBACK_SOURCE_HUMAN,
    FEEDBACK_STATUS_APPLIED,
    FEEDBACK_STATUS_DROPPED,
    FEEDBACK_STATUS_MIGRATED,
    LOG_FEEDBACK_APPLIED,
    LOG_FEEDBACK_SETTLED,
    STATE_FIELD_FEEDBACK_HISTORY,
    STATE_FIELD_FEEDBACK_NOTES,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_CURRENT_PHASE,
    STATE_FIELD_PHASE_FEEDBACK,
    STATE_FIELD_PHASE_STATUS,
    STATE_FIELD_PROJECT_ID,
)

logger = structlog.get_logger()


class FeedbackNote(TypedDict):
    """An active note with who wrote it and when."""

    note: str
    source: str
    added_at: str


class FeedbackHistoryEntry(TypedDict):
    """A consumed note: the active entry plus how and when it left."""

    note: str
    source: str
    added_at: str
    status: str
    settled_at: str


@dataclass(frozen=True)
class NewFeedbackNote:
    """A reviewer note to file under ``phase``."""

    phase: str
    note: str
    source: str = FEEDBACK_SOURCE_HUMAN


@dataclass(frozen=True)
class _Active:
    """One active note text, with its tag when it has one (legacy: None)."""

    text: str
    tag: FeedbackNote | None


# Decides the history status of an active note, or None to keep it active.
_SettleRule = Callable[[_Active], str | None]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _phase_map(state: Mapping[str, object], field: str) -> dict[str, object]:
    raw = state.get(field)
    return dict(raw) if isinstance(raw, dict) else {}


def _active_texts(state: Mapping[str, object], phase: str) -> list[str]:
    raw = _phase_map(state, STATE_FIELD_PHASE_FEEDBACK).get(phase)
    if not isinstance(raw, list):
        return []
    return [str(note) for note in raw if str(note).strip()]


def _as_note(raw: object) -> FeedbackNote | None:
    if not isinstance(raw, dict) or not isinstance(raw.get(FEEDBACK_ENTRY_NOTE), str):
        return None
    return FeedbackNote(
        note=str(raw[FEEDBACK_ENTRY_NOTE]),
        source=str(raw.get(FEEDBACK_ENTRY_SOURCE) or FEEDBACK_SOURCE_HUMAN),
        added_at=str(raw.get(FEEDBACK_ENTRY_ADDED_AT) or ""),
    )


def _tagged_notes(state: Mapping[str, object], phase: str) -> list[FeedbackNote]:
    raw = _phase_map(state, STATE_FIELD_FEEDBACK_NOTES).get(phase)
    if not isinstance(raw, list):
        return []
    return [note for note in (_as_note(item) for item in raw) if note is not None]


def _active_notes(state: Mapping[str, object], phase: str) -> list[_Active]:
    """Active texts in order, each matched to its tag (untagged = legacy)."""
    pool = _tagged_notes(state, phase)
    active: list[_Active] = []
    for text in _active_texts(state, phase):
        tag = next((note for note in pool if note["note"] == text), None)
        if tag is not None:
            pool.remove(tag)
        active.append(_Active(text=text, tag=tag))
    return active


def active_feedback_notes(state: Mapping[str, object], phase: str) -> list[str]:
    """The note texts the next regeneration of ``phase`` will use."""
    return _active_texts(state, phase)


def feedback_history(
    state: Mapping[str, object], phase: str
) -> list[FeedbackHistoryEntry]:
    """Consumed notes of ``phase``, oldest first (persona feedback loop, AC6)."""
    raw = _phase_map(state, STATE_FIELD_FEEDBACK_HISTORY).get(phase)
    if not isinstance(raw, list):
        return []
    entries: list[FeedbackHistoryEntry] = []
    for item in raw:
        note = _as_note(item)
        if note is None or not isinstance(item, dict):
            continue
        entries.append(
            FeedbackHistoryEntry(
                **note,
                status=str(item.get(FEEDBACK_ENTRY_STATUS) or ""),
                settled_at=str(item.get(FEEDBACK_ENTRY_SETTLED_AT) or ""),
            )
        )
    return entries


def add_feedback_note(
    state: Mapping[str, object], new: NewFeedbackNote
) -> dict[str, object]:
    """Updates filing ``new`` as an active, tagged note."""
    texts = _phase_map(state, STATE_FIELD_PHASE_FEEDBACK)
    texts[new.phase] = [*_active_texts(state, new.phase), new.note]
    notes = _phase_map(state, STATE_FIELD_FEEDBACK_NOTES)
    tag = FeedbackNote(note=new.note, source=new.source, added_at=_now())
    notes[new.phase] = [*_tagged_notes(state, new.phase), tag]
    return {STATE_FIELD_PHASE_FEEDBACK: texts, STATE_FIELD_FEEDBACK_NOTES: notes}


def _history_entry(active: _Active, status: str) -> dict[str, object]:
    tag = active.tag or FeedbackNote(
        note=active.text, source=FEEDBACK_SOURCE_HUMAN, added_at=""
    )
    return {**tag, FEEDBACK_ENTRY_STATUS: status, FEEDBACK_ENTRY_SETTLED_AT: _now()}


def _settle(
    state: Mapping[str, object], phase: str, rule: _SettleRule
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Move the notes ``rule`` settles to history; returns (updates, moved)."""
    kept: list[_Active] = []
    moved: list[dict[str, object]] = []
    for active in _active_notes(state, phase):
        status = rule(active)
        if status is None:
            kept.append(active)
            continue
        moved.append(_history_entry(active, status))
    if not moved:
        return {}, []
    return _settled_updates(state, phase, (kept, moved)), moved


def _settled_updates(
    state: Mapping[str, object],
    phase: str,
    split: tuple[list[_Active], list[dict[str, object]]],
) -> dict[str, object]:
    kept, moved = split
    texts = _phase_map(state, STATE_FIELD_PHASE_FEEDBACK)
    texts[phase] = [active.text for active in kept]
    notes = _phase_map(state, STATE_FIELD_FEEDBACK_NOTES)
    notes[phase] = [active.tag for active in kept if active.tag is not None]
    history = _phase_map(state, STATE_FIELD_FEEDBACK_HISTORY)
    prior = history.get(phase)
    history[phase] = [*(prior if isinstance(prior, list) else []), *moved]
    return {
        STATE_FIELD_PHASE_FEEDBACK: texts,
        STATE_FIELD_FEEDBACK_NOTES: notes,
        STATE_FIELD_FEEDBACK_HISTORY: history,
    }


def _log(
    event: str, state: Mapping[str, object], moved: list[dict[str, object]]
) -> None:
    logger.info(
        event,
        project_id=str(state.get(STATE_FIELD_PROJECT_ID, "")),
        notes=len(moved),
        statuses=sorted({str(entry[FEEDBACK_ENTRY_STATUS]) for entry in moved}),
        sources=sorted({str(entry[FEEDBACK_ENTRY_SOURCE]) for entry in moved}),
    )


def consume_feedback_notes(
    state: Mapping[str, object], phase: str
) -> dict[str, object]:
    """Updates marking every active ``phase`` note applied (it was just used)."""
    updates, moved = _settle(state, phase, lambda _active: FEEDBACK_STATUS_APPLIED)
    if moved:
        _log(LOG_FEEDBACK_APPLIED, state, moved)
    return updates


def _stale_rule(state: Mapping[str, object], action: str) -> _SettleRule:
    regen_failed = state.get(STATE_FIELD_PHASE_STATUS) == PHASE_STATUS_FAILED
    content_approved = (
        action == REVIEW_ACTION_APPROVE
        and state.get(STATE_FIELD_CURRENT_PHASE) == PHASE_CONTENT
    )

    def rule(active: _Active) -> str | None:
        if active.tag is None:
            return None if regen_failed else FEEDBACK_STATUS_MIGRATED
        if content_approved and active.tag["source"] == FEEDBACK_SOURCE_AUTOPILOT:
            return FEEDBACK_STATUS_DROPPED
        return None

    return rule


def settle_stale_content_feedback(
    state: Mapping[str, object], action: str
) -> dict[str, object]:
    """Updates settling content notes no regeneration will use (on resume).

    Legacy untagged notes predate the last regeneration (the checkpoint only
    holds them after one ran) unless that regeneration failed: they migrate.
    An active autopilot note is dropped when the content gate is approved: the
    gate reason it was written for no longer holds.
    """
    updates, moved = _settle(state, PHASE_CONTENT, _stale_rule(state, action))
    if moved:
        _log(LOG_FEEDBACK_SETTLED, state, moved)
    return updates


__all__ = [
    "FeedbackHistoryEntry",
    "FeedbackNote",
    "NewFeedbackNote",
    "active_feedback_notes",
    "add_feedback_note",
    "consume_feedback_notes",
    "feedback_history",
    "settle_stale_content_feedback",
]
