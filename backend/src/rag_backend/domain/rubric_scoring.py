"""One scale for rubric thresholds, and safe criterion prompt rendering.

A criterion's ``min_threshold`` is a fraction (0.0-1.0) of its scoring scale,
the range the rubric API accepts. Scores keep their scale (0-100, 1-10) and
are compared as a fraction of the scale maximum. Rubrics stored before the
fraction scale hold a value on the criterion's scale (e.g. 70.0 on 0-100, 7.0
on 1-10); any stored threshold above 1.0 is read that way. Only reads
normalise: the rubric API rejects a threshold above 1.0 on create and update.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

from rag_backend.domain.models.rubric import RubricCriterion, ScoringScale

PERCENT: Final = 100.0
MAX_FRACTION: Final = 1.0
PERCENT_DECIMALS: Final = 2
DEFAULT_SCALE_MAX: Final = PERCENT
SCALE_MAX: Final[Mapping[str, float]] = {
    ScoringScale.SCORE_0_100.value: PERCENT,
    ScoringScale.SCORE_1_10.value: 10.0,
}
THRESHOLD_KEY: Final = "min_threshold"
SCALE_KEY: Final = "scoring_scale"
_PLACEHOLDER: Final = re.compile(r"\{(content|sources)\}")


def scale_max(scale: object) -> float:
    """The maximum score of a scoring scale (100 for scales without a numeric max)."""
    return SCALE_MAX.get(str(scale), DEFAULT_SCALE_MAX)


def normalize_threshold(value: float, scale: object) -> float:
    """The threshold as a fraction of its scale.

    A legacy value above 1.0 is read on the criterion's scale (7 on 1-10 is
    0.7); one above the scale maximum is read as a percentage (70 on 1-10 is
    0.7). The result never exceeds 1.0.
    """
    if value <= MAX_FRACTION:
        return value
    maximum = scale_max(scale)
    divisor = maximum if value <= maximum else PERCENT
    return min(value / divisor, MAX_FRACTION)


def _criterion_fraction(criterion: RubricCriterion) -> float:
    return normalize_threshold(criterion["min_threshold"], criterion["scoring_scale"])


def threshold_percent(criterion: RubricCriterion) -> float:
    """The threshold as a percentage of the scale (for prompts that say ``/100``)."""
    return round(_criterion_fraction(criterion) * PERCENT, PERCENT_DECIMALS)


def criterion_passes(criterion: RubricCriterion, score: float) -> bool:
    """True when the score reaches the threshold on the criterion's own scale."""
    return score / scale_max(criterion["scoring_scale"]) >= _criterion_fraction(
        criterion
    )


def normalize_stored_criterion(criterion: Mapping[str, object]) -> dict[str, object]:
    """A stored criterion with its numeric threshold on the fraction scale."""
    updated = dict(criterion)
    threshold = updated.get(THRESHOLD_KEY)
    if isinstance(threshold, int | float) and not isinstance(threshold, bool):
        updated[THRESHOLD_KEY] = normalize_threshold(
            float(threshold), updated.get(SCALE_KEY)
        )
    return updated


def normalize_criteria(criteria: list[RubricCriterion]) -> list[RubricCriterion]:
    """Stored criteria with every numeric threshold on the fraction scale."""
    normalized: list[RubricCriterion] = []
    for criterion in criteria:
        updated = criterion.copy()
        threshold = updated.get(THRESHOLD_KEY)
        if isinstance(threshold, int | float):
            updated[THRESHOLD_KEY] = normalize_threshold(
                float(threshold), updated.get(SCALE_KEY)
            )
        normalized.append(updated)
    return normalized


def render_criterion_prompt(template: str, content: str, sources: list[str]) -> str:
    """Fill ``{content}`` and ``{sources}`` in one pass; other braces stay literal.

    ``str.format`` raised on any other ``{...}`` in a custom template (a JSON
    example, a ``{score}`` hint), which crashed the evaluation.
    """
    values = {"content": content, "sources": str(sources)}
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
