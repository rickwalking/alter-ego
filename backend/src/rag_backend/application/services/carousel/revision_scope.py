"""Keep a revision inside the slides it names (QA F-10).

Prod carousel 7acaf967: revision 1 asked to change only slides 2 and 6, yet
every slide was re-drafted and stored, so slides 1, 3 and 7 changed and slide
3 lost its 3 features. The prompt said "change only the listed slides"; the
code regenerated and replaced the whole deck.

Now the scope is enforced in code:

- ``revision_scope``: the slides the active revision notes name ("slide 6",
  "slides 2 e 6", "slides 2-4", the autopilot's "slide 6 (pt body): ..."),
  plus the slides the content gate currently blocks. ``None`` when no note
  names a slide: a general note ("make it shorter") still rewrites the deck.
- ``SlideDraftGenerationParams.only_slides``: only those slides are drafted
  (each still sees the whole outline as sibling context).
- ``merge_scoped_drafts``: the fresh drafts replace only their own slides.
- ``keep_unscoped_slides``: after the review build, every slide outside the
  scope gets its stored localized copy back (written like an owner edit, so
  drafts, translations and both validation reports stay in step).

Slide lists are read in forms like "slide 6", "Slides 2 e 6", "slides 2, 3 and 7",
"slides 2-4" and "slide nº 5".
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.domain.constants.carousel_presentation import SEVERITY_BLOCKER
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_BLOCKING,
    STATE_FIELD_CONTENT_GATE_VALIDATION,
    STATE_FIELD_LOCALIZED_SLIDES,
    STATE_FIELD_SLIDE_DRAFTS,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_VIOLATIONS,
)

_SLIDE_LIST = re.compile(
    r"\bslides?\s*(?:n[º°o.]\s*)?#?\s*"
    r"(\d{1,2}(?:\s*(?:,|/|&|-|\u2013|\be\b|\band\b|\bou\b|\bor\b)\s*\d{1,2})*)",
    flags=re.IGNORECASE,
)
_RANGE = re.compile(r"(\d{1,2})\s*[-\u2013]\s*(\d{1,2})")
_NUMBER = re.compile(r"\d{1,2}")
_SEVERITY_KEY = "severity"


def _numbers(group: str) -> set[int]:
    found: set[int] = set()
    for start, end in _RANGE.findall(group):
        low, high = sorted((int(start), int(end)))
        found.update(range(low, high + 1))
    found.update(int(number) for number in _NUMBER.findall(_RANGE.sub("", group)))
    return found


def named_slides(notes: list[str]) -> frozenset[int]:
    """Every slide number the notes name."""
    named: set[int] = set()
    for note in notes:
        for match in _SLIDE_LIST.finditer(note):
            named.update(_numbers(match.group(1)))
    return frozenset(number for number in named if number > 0)


def blocked_slides(state: Mapping[str, object]) -> frozenset[int]:
    """Slides the stored content gate blocks."""
    gate = state.get(STATE_FIELD_CONTENT_GATE_VALIDATION)
    if not isinstance(gate, Mapping) or gate.get(STATE_FIELD_BLOCKING) is not True:
        return frozenset()
    raw = gate.get(STATE_FIELD_VIOLATIONS)
    violations = raw if isinstance(raw, list) else []
    return frozenset(
        index
        for violation in violations
        if isinstance(violation, Mapping)
        and violation.get(_SEVERITY_KEY, SEVERITY_BLOCKER) == SEVERITY_BLOCKER
        and isinstance(index := violation.get(STATE_FIELD_SLIDE_INDEX), int)
    )


def _dicts(value: object) -> list[dict[str, object]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _index(item: Mapping[str, object], position: int) -> int:
    value = item.get(STATE_FIELD_SLIDE_INDEX)
    return value if isinstance(value, int) else position


def revision_scope(
    state: Mapping[str, object], notes: list[str]
) -> frozenset[int] | None:
    """The slides this revision may change; None means the whole deck.

    Scoping needs stored slides to keep: a first draft is never scoped.
    """
    named = named_slides(notes)
    stored = _dicts(state.get(STATE_FIELD_LOCALIZED_SLIDES))
    if not named or not stored or not _dicts(state.get(STATE_FIELD_SLIDE_DRAFTS)):
        return None
    known = {_index(slide, position) for position, slide in enumerate(stored, 1)}
    scope = (named | blocked_slides(state)) & known
    return frozenset(scope) if scope else None


def merge_scoped_drafts(
    stored: list[dict[str, object]],
    fresh: list[dict[str, object]],
    scope: frozenset[int],
) -> list[dict[str, object]]:
    """The stored drafts with each fresh in-scope draft replacing its slide."""
    by_index = {
        index: draft
        for position, draft in enumerate(fresh, start=1)
        if (index := _index(draft, position)) in scope
    }
    return [
        by_index.get(_index(draft, position), draft)
        for position, draft in enumerate(stored, start=1)
    ]


def scoped_draft_updates(
    state: Mapping[str, object],
    draft_updates: dict[str, object],
    scope: frozenset[int] | None,
) -> dict[str, object]:
    """Draft updates whose ``slide_drafts`` keep the stored unscoped drafts."""
    fresh = _dicts(draft_updates.get(STATE_FIELD_SLIDE_DRAFTS))
    if scope is None or not fresh:
        return draft_updates
    stored = _dicts(state.get(STATE_FIELD_SLIDE_DRAFTS))
    merged = merge_scoped_drafts(stored, fresh, scope)
    return {**draft_updates, STATE_FIELD_SLIDE_DRAFTS: merged}


def keep_unscoped_slides(
    state: Mapping[str, object],
    updates: Mapping[str, object],
    scope: frozenset[int],
) -> dict[str, object]:
    """Updates that keep every slide outside ``scope`` as it was stored."""
    stored = _dicts(state.get(STATE_FIELD_LOCALIZED_SLIDES))
    rebuilt = _dicts(updates.get(STATE_FIELD_LOCALIZED_SLIDES))
    if not stored or not rebuilt:
        return {}
    fresh = [
        slide
        for position, slide in enumerate(rebuilt, start=1)
        if _index(slide, position) in scope
    ]
    base = {**state, **updates, STATE_FIELD_LOCALIZED_SLIDES: stored}
    return apply_localized_slide_edits(base, fresh)


__all__ = [
    "blocked_slides",
    "keep_unscoped_slides",
    "merge_scoped_drafts",
    "named_slides",
    "revision_scope",
    "scoped_draft_updates",
]
