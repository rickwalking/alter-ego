"""Persona voice scores on one 0-100 scale, on every read path (AE-0407). Pure.

The judge's prompt does not name the scale and the fast model often answers
on 0-10 (prod be190a0c: a stored ``overall`` of 8.7 was compared with the
0-100 floor 70). A stored ``overall`` in (0, 10] is therefore a 0-10 answer
and is read x10. A 0, a missing or a non-numeric ``overall`` is a failed
judge call, not a verdict: it reads as unscored (None), never as low.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from rag_backend.domain.constants.carousel_workflow import PERSONA_SCORE_OVERALL_KEY
from rag_backend.domain.constants.persona import (
    PERSONA_SCORE_TEN_POINT_MAX,
    PERSONA_SCORE_TEN_TO_HUNDRED,
)


def on_hundred_scale(value: float) -> float:
    """A score in (0, 10] is a 0-10 answer: x10. Anything else is kept."""
    if 0 < value <= PERSONA_SCORE_TEN_POINT_MAX:
        return value * PERSONA_SCORE_TEN_TO_HUNDRED
    return value


def stored_overall(entry: object) -> float | None:
    """One persona-score entry's overall on 0-100; None when unscored.

    ``entry`` is the stored ``{"overall": ..., ...}`` dict or a bare number.
    """
    raw = entry.get(PERSONA_SCORE_OVERALL_KEY) if isinstance(entry, Mapping) else entry
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return None
    value = float(raw)
    if math.isnan(value) or value <= 0:
        return None
    return on_hundred_scale(value)


def lowest_overall(scores: object) -> float | None:
    """The lowest scored overall of a ``persona_scores`` map; None if none."""
    if not isinstance(scores, Mapping):
        return None
    values = [stored_overall(entry) for entry in scores.values()]
    scored = [value for value in values if value is not None]
    return min(scored) if scored else None


__all__ = ["lowest_overall", "on_hundred_scale", "stored_overall"]
