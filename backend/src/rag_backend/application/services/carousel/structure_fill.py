"""Fill a slide's missing structured items deterministically (AE-0367, AE-0437).

Pure: no DB, no LLM. Shared by the owner autofix (AE-0367) and the content
gate repair (AE-0430), so both fix the same structural gaps the same way:

- a content slide without a body gets 3-4 features from its outline key points;
- a summary slide without 3 complete points gets them from its key points, or
  else from the titles and first key points of the content slides;
- a closing slide without 3 complete actions (AE-0437, prod carousel 7acaf967:
  ``closing_actions_missing`` survived generation, repair and one revision)
  first gets its own complete ``features`` moved under ``actions`` (the key a
  revision or a manual edit swapped, carousel 5344b6c6), else 3 actions from
  its outline key points.

The EN side gets the PT items it lacks (``mirror_missing_items``); those
copies are Portuguese, so the caller translates them afterwards.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field

from rag_backend.application.services.carousel.owner_autofix_fill import (
    CLOSING_BUDGET,
    FEATURE_BUDGET,
    SUMMARY_BUDGET,
    FillSource,
    build_items,
    key_point_pairs,
)
from rag_backend.application.services.carousel.owner_autofix_paths import (
    complete_items,
)
from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.carousel_autofix import FILL_MIN_ITEMS
from rag_backend.domain.constants.carousel_presentation import MIN_CLOSING_ACTIONS
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_OUTLINE,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
)

_FEATURES = "features"
_SUMMARY_POINTS = "summary_points"
_ACTIONS = "actions"
_BODY = "body"
_TITLE = "title"
_KEY_POINTS = "key_points"


@dataclass(frozen=True)
class SlideOutline:
    """The outline entry of one slide."""

    title: str = ""
    key_points: tuple[str, ...] = ()
    slide_type: str = ""


@dataclass(frozen=True)
class StructureFillContext:
    """The contract's allowed icons and the outline, by slide index."""

    icons: tuple[str, ...] = ()
    outline: Mapping[int, SlideOutline] = field(default_factory=dict)


@dataclass(frozen=True)
class SlideRef:
    """Which slide a payload belongs to."""

    index: int
    slide_type: str


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def outline_from_state(state: Mapping[str, object] | None) -> dict[int, SlideOutline]:
    """The workflow state's outline by slide index (position when unnumbered)."""
    raw = state.get(STATE_FIELD_OUTLINE) if state is not None else None
    entries = (
        [item for item in raw if isinstance(item, Mapping)]
        if isinstance(raw, list)
        else []
    )
    outline: dict[int, SlideOutline] = {}
    for position, item in enumerate(entries, start=1):
        index = item.get(STATE_FIELD_SLIDE_INDEX)
        outline[index if isinstance(index, int) else position] = SlideOutline(
            title=str(item.get(_TITLE) or "").strip(),
            key_points=_strings(item.get(_KEY_POINTS)),
            slide_type=str(item.get(STATE_FIELD_SLIDE_TYPE) or ""),
        )
    return outline


def _summary_pairs(
    index: int, context: StructureFillContext
) -> tuple[tuple[str, str], ...]:
    own = context.outline.get(index, SlideOutline())
    pairs = key_point_pairs(own.key_points, SUMMARY_BUDGET.title)
    if len(pairs) >= FILL_MIN_ITEMS:
        return pairs
    return tuple(
        (entry.title, entry.key_points[0])
        for _, entry in sorted(context.outline.items())
        if entry.slide_type == SLIDE_TYPE_CONTENT and entry.title and entry.key_points
    )


def needs_features(payload: Mapping[str, object], slide_type: str) -> bool:
    """A content slide without a body and fewer than 3 complete features."""
    if slide_type != SLIDE_TYPE_CONTENT or str(payload.get(_BODY) or "").strip():
        return False
    return complete_items(payload, _FEATURES) < FILL_MIN_ITEMS


def needs_summary(payload: Mapping[str, object], slide_type: str) -> bool:
    """A summary slide with fewer than 3 complete points."""
    if slide_type != SLIDE_TYPE_SUMMARY:
        return False
    return complete_items(payload, _SUMMARY_POINTS) < FILL_MIN_ITEMS


def needs_actions(payload: Mapping[str, object], slide_type: str) -> bool:
    """A closing slide with fewer than 3 complete actions (AE-0437)."""
    if slide_type != SLIDE_TYPE_CLOSING:
        return False
    return complete_items(payload, _ACTIONS) < MIN_CLOSING_ACTIONS


def _feature_items(
    slide: SlideRef, context: StructureFillContext
) -> list[dict[str, object]] | None:
    points = context.outline.get(slide.index, SlideOutline()).key_points
    return build_items(
        FillSource(
            pairs=key_point_pairs(points, FEATURE_BUDGET.title),
            icons=context.icons,
            budget=FEATURE_BUDGET,
        )
    )


def _summary_items(
    slide: SlideRef, context: StructureFillContext
) -> list[dict[str, object]] | None:
    return build_items(
        FillSource(
            pairs=_summary_pairs(slide.index, context),
            icons=context.icons,
            budget=SUMMARY_BUDGET,
        )
    )


def _action_items(
    slide: SlideRef, context: StructureFillContext
) -> list[dict[str, object]] | None:
    points = context.outline.get(slide.index, SlideOutline()).key_points
    pairs = key_point_pairs(points, CLOSING_BUDGET.title)[:MIN_CLOSING_ACTIONS]
    return build_items(
        FillSource(pairs=pairs, icons=context.icons, budget=CLOSING_BUDGET)
    )


def move_closing_features(payload: dict[str, object], slide_type: str) -> bool:
    """Move a closing slide's complete features under ``actions``, in place.

    Only when the actions are incomplete and the features alone satisfy the
    closing rule: the texts are right, only the key is wrong (AE-0437).
    """
    if not needs_actions(payload, slide_type):
        return False
    if complete_items(payload, _FEATURES) < MIN_CLOSING_ACTIONS:
        return False
    payload[_ACTIONS] = payload.pop(_FEATURES)
    return True


def _fill_actions(
    payload: dict[str, object], slide: SlideRef, context: StructureFillContext
) -> None:
    if move_closing_features(payload, slide.slide_type):
        return
    if not needs_actions(payload, slide.slide_type):
        return
    actions = _action_items(slide, context)
    if actions is not None:
        payload[_ACTIONS] = actions


def fill_missing_items(
    payload: dict[str, object], slide: SlideRef, context: StructureFillContext
) -> None:
    """Fill a PT payload's missing features, summary points and actions in place."""
    if needs_features(payload, slide.slide_type):
        features = _feature_items(slide, context)
        if features is not None:
            payload[_FEATURES] = features
    if needs_summary(payload, slide.slide_type):
        points = _summary_items(slide, context)
        if points is not None:
            payload[_SUMMARY_POINTS] = points
    _fill_actions(payload, slide, context)


def mirror_missing_items(
    english: dict[str, object], portuguese: Mapping[str, object], slide: SlideRef
) -> tuple[str, ...]:
    """Give the EN payload the PT items it lacks; return the lists copied.

    A closing EN payload first gets its own swapped features moved back under
    ``actions`` (already English, nothing to translate). The copied items are
    Portuguese, so all of them are translated afterwards.
    """
    move_closing_features(english, slide.slide_type)
    copied: list[str] = []
    checks = (
        (_FEATURES, needs_features),
        (_SUMMARY_POINTS, needs_summary),
        (_ACTIONS, needs_actions),
    )
    for list_field, needs in checks:
        if needs(english, slide.slide_type) and complete_items(portuguese, list_field):
            english[list_field] = copy.deepcopy(portuguese[list_field])
            copied.append(list_field)
    return tuple(copied)


__all__ = [
    "SlideOutline",
    "SlideRef",
    "StructureFillContext",
    "fill_missing_items",
    "mirror_missing_items",
    "move_closing_features",
    "needs_actions",
    "needs_features",
    "needs_summary",
    "outline_from_state",
]
