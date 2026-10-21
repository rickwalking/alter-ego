"""Persona voice scores on one 0-100 scale, on every read path. Pure.

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
from rag_backend.domain.constants.slide_fix import (
    PERSONA_SCORE_RESCORE_PENDING_KEY,
    PERSONA_SCORE_SLIDE_KEY,
    PERSONA_SCORE_UNSCORED_TICKS_KEY,
)


def on_hundred_scale(value: float) -> float:
    """A score in (0, 10] is a 0-10 answer: x10. Anything else is kept."""
    if 0 < value <= PERSONA_SCORE_TEN_POINT_MAX:
        return value * PERSONA_SCORE_TEN_TO_HUNDRED
    return value


def on_hundred_scale_entry(entry: Mapping[str, object]) -> dict[str, object]:
    """One judge entry with every numeric score on 0-100.

    The ``overall`` is scaled by itself (the gate's score); the other
    numeric fields are scaled together, only when ALL of them are at most
    10 (a 0-10 answer, as in ``PersonaAgent._parse_evaluation_response``).
    Non-numeric fields (``suggestions``, markers) pass through untouched,
    so a stored ``rescore_pending`` marker survives the normalization; the
    ``unscored_ticks`` counter is a tick count, not a score, and is never
    scaled.
    """
    numeric = {
        key: value
        for key, value in entry.items()
        if key != PERSONA_SCORE_UNSCORED_TICKS_KEY
        and isinstance(value, int | float)
        and not isinstance(value, bool)
    }
    scaled: dict[str, object] = dict(entry)
    if numeric and not any(
        value > PERSONA_SCORE_TEN_POINT_MAX for value in numeric.values()
    ):
        scaled.update({
            key: value * PERSONA_SCORE_TEN_TO_HUNDRED for key, value in numeric.items()
        })
    overall = entry.get(PERSONA_SCORE_OVERALL_KEY)
    if isinstance(overall, int | float) and not isinstance(overall, bool):
        scaled[PERSONA_SCORE_OVERALL_KEY] = on_hundred_scale(float(overall))
    return scaled


def pending_rescores(scores: object) -> dict[int, int]:
    """Pending ``slide_N`` entries by index, with their ticks.

    An entry marked ``rescore_pending`` carries a STALE ``overall``: it
    awaits a re-score. The ticks count how often the judge stayed
    unscored; a missing or malformed tick reads as 1.
    """
    if not isinstance(scores, Mapping):
        return {}
    prefix = PERSONA_SCORE_SLIDE_KEY.format(index="")
    pending: dict[int, int] = {}
    for key, value in scores.items():
        text = str(key)
        if not text.startswith(prefix):
            continue
        suffix = text.removeprefix(prefix)
        if not suffix.isdigit():
            continue
        if not isinstance(value, Mapping):
            continue
        if value.get(PERSONA_SCORE_RESCORE_PENDING_KEY) is not True:
            continue
        ticks = value.get(PERSONA_SCORE_UNSCORED_TICKS_KEY)
        if isinstance(ticks, bool) or not isinstance(ticks, int):
            pending[int(suffix)] = 1
        else:
            pending[int(suffix)] = max(1, ticks)
    return pending


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


__all__ = [
    "lowest_overall",
    "on_hundred_scale",
    "on_hundred_scale_entry",
    "pending_rescores",
    "stored_overall",
]
