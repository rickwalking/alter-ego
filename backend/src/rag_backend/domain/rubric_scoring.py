"""One scale for rubric thresholds, and safe criterion prompt rendering.

A criterion's ``min_threshold`` is a fraction (0.0-1.0) of its scoring scale,
the range the rubric API accepts. Scores keep their scale (0-100, 1-10) and
are compared as a fraction of the scale maximum. Rubrics stored before the
fraction scale hold percentages (e.g. 70.0); any threshold above 1.0 is read
as a percentage.
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
_PLACEHOLDER: Final = re.compile(r"\{(content|sources)\}")


def normalize_threshold(value: float) -> float:
    """The threshold as a fraction; a legacy percentage above 1.0 is divided by 100."""
    return value / PERCENT if value > MAX_FRACTION else value


def threshold_percent(criterion: RubricCriterion) -> float:
    """The threshold as a percentage of the scale (for prompts that say ``/100``)."""
    return round(
        normalize_threshold(criterion["min_threshold"]) * PERCENT, PERCENT_DECIMALS
    )


def criterion_passes(criterion: RubricCriterion, score: float) -> bool:
    """True when the score reaches the threshold on the criterion's own scale."""
    scale_max = SCALE_MAX.get(str(criterion["scoring_scale"]), DEFAULT_SCALE_MAX)
    return score / scale_max >= normalize_threshold(criterion["min_threshold"])


def normalize_criteria(criteria: list[RubricCriterion]) -> list[RubricCriterion]:
    """Stored criteria with every numeric threshold on the fraction scale."""
    normalized: list[RubricCriterion] = []
    for criterion in criteria:
        updated = criterion.copy()
        threshold = updated.get(THRESHOLD_KEY)
        if isinstance(threshold, int | float):
            updated[THRESHOLD_KEY] = normalize_threshold(float(threshold))
        normalized.append(updated)
    return normalized


def render_criterion_prompt(template: str, content: str, sources: list[str]) -> str:
    """Fill ``{content}`` and ``{sources}`` in one pass; other braces stay literal.

    ``str.format`` raised on any other ``{...}`` in a custom template (a JSON
    example, a ``{score}`` hint), which crashed the evaluation.
    """
    values = {"content": content, "sources": str(sources)}
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
