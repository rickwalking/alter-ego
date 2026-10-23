"""Turn a judge's per-criterion answers into a carousel's rubric evaluation.

Scores are on 0-100 whatever a criterion's own scale (the judge is told so);
an answer outside the range is clamped. A criterion passes at or above its
threshold as a percentage of its scale. The overall score is the weight-averaged
criterion score, rounded to an integer (``rubric_evaluation_scores.overall_score``
is an integer column read as a percentage). The carousel passes when every
criterion does. A criterion the judge left out is scored 0 and fails.
"""

from __future__ import annotations

from collections.abc import Sequence

from rag_backend.domain.constants.carousel_rubric import RUBRIC_SCORE_SCALE
from rag_backend.domain.models.carousel_rubric import (
    CarouselRubric,
    CarouselRubricEvaluation,
    CriterionScore,
    JudgedCriterion,
)
from rag_backend.domain.models.rubric import RubricCriterion
from rag_backend.domain.rubric_scoring import threshold_percent


def _clamped(score: float) -> int:
    return round(min(max(score, 0.0), float(RUBRIC_SCORE_SCALE)))


def _weight(criterion: RubricCriterion) -> float:
    weight = criterion.get("weight", 1.0)
    return float(weight) if weight and weight > 0 else 1.0


def _criterion_score(
    criterion: RubricCriterion, answers: dict[str, JudgedCriterion]
) -> CriterionScore:
    answer = answers.get(criterion["id"])
    score = _clamped(answer.score) if answer else 0
    threshold = round(threshold_percent(criterion))
    return CriterionScore(
        criterion_id=criterion["id"],
        name=criterion["name"],
        score=score,
        threshold=threshold,
        passed=score >= threshold,
        feedback=answer.feedback if answer else "",
        description=str(criterion.get("description", "")),
        scale=str(criterion.get("scoring_scale", "")),
        weight=_weight(criterion),
    )


def build_rubric_evaluation(
    rubric: CarouselRubric,
    answers: Sequence[JudgedCriterion],
    feedback: str = "",
) -> CarouselRubricEvaluation:
    """The evaluation of ``rubric`` from the judge's ``answers``."""
    by_id = {answer.criterion_id: answer for answer in answers}
    scores = tuple(_criterion_score(c, by_id) for c in rubric.criteria)
    weights = [_weight(c) for c in rubric.criteria]
    total = sum(weights)
    overall = (
        sum(s.score * w for s, w in zip(scores, weights, strict=True)) / total
        if total
        else 0.0
    )
    return CarouselRubricEvaluation(
        rubric_id=rubric.id,
        rubric_name=rubric.name,
        overall_score=_clamped(overall),
        passed=bool(scores) and all(s.passed for s in scores),
        criteria=scores,
        feedback=feedback,
        rubric_version=rubric.version,
    )


__all__ = ["build_rubric_evaluation"]
