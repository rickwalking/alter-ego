"""A judge's answers become a carousel's 0-100 rubric evaluation.

Feature: backend/tests/features/carousel_rubric_ae0504.feature
"""

from __future__ import annotations

from rag_backend.domain.carousel_rubric_scoring import build_rubric_evaluation
from rag_backend.domain.models.carousel_rubric import CarouselRubric, JudgedCriterion
from rag_backend.domain.models.rubric import (
    EvaluationMethod,
    RubricCriterion,
    ScoringScale,
)


def _criterion(
    criterion_id: str, threshold: float, weight: float = 1.0
) -> RubricCriterion:
    return RubricCriterion(
        id=criterion_id,
        name=criterion_id.title(),
        description=f"{criterion_id} description",
        weight=weight,
        evaluation_method=EvaluationMethod.AI_AUTO,
        min_threshold=threshold,
        scoring_scale=ScoringScale.SCORE_0_100,
        prompt_template="Rate {content}",
    )


RUBRIC = CarouselRubric(
    id="rubric-qa",
    name="QA",
    criteria=(_criterion("clarity", 0.7, 2.0), _criterion("hook", 0.6)),
)


def test_scores_thresholds_and_weighted_overall() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    evaluation = build_rubric_evaluation(
        RUBRIC,
        [JudgedCriterion("clarity", 80, "clear"), JudgedCriterion("hook", 65.4)],
        "good",
    )

    assert [
        (c.criterion_id, c.score, c.threshold, c.passed) for c in evaluation.criteria
    ] == [
        ("clarity", 80, 70, True),
        ("hook", 65, 60, True),
    ]
    assert evaluation.overall_score == round((80 * 2 + 65) / 3)
    assert evaluation.passed is True
    assert evaluation.feedback == "good"
    assert evaluation.to_state()["criteria"] == [
        {
            "id": "clarity",
            "name": "Clarity",
            "score": 80,
            "threshold": 70,
            "passed": True,
            "feedback": "clear",
        },
        {
            "id": "hook",
            "name": "Hook",
            "score": 65,
            "threshold": 60,
            "passed": True,
            "feedback": "",
        },
    ]
    assert evaluation.criterion_rows()["hook"] == {
        "name": "Hook",
        "score": 65,
        "threshold": 60,
        "passed": True,
    }


def test_a_criterion_below_threshold_fails_the_carousel() -> None:
    """Scenario: A criterion below its threshold is flagged."""
    evaluation = build_rubric_evaluation(
        RUBRIC, [JudgedCriterion("clarity", 69), JudgedCriterion("hook", 100)]
    )

    assert [c.passed for c in evaluation.criteria] == [False, True]
    assert evaluation.passed is False


def test_out_of_range_and_missing_answers() -> None:
    """Scenario: A criterion below its threshold is flagged."""
    evaluation = build_rubric_evaluation(
        RUBRIC, [JudgedCriterion("clarity", 140), JudgedCriterion("unknown", 50)]
    )

    clarity, hook = evaluation.criteria
    assert (clarity.score, clarity.passed) == (100, True)
    assert (hook.score, hook.passed) == (0, False)
    assert evaluation.overall_score == round(200 / 3)


def test_legacy_threshold_and_zero_weight() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    rubric = CarouselRubric(
        id="legacy", name="Legacy", criteria=(_criterion("voice", 75.0, 0.0),)
    )
    evaluation = build_rubric_evaluation(rubric, [JudgedCriterion("voice", -5)])

    assert evaluation.criteria[0].threshold == 75
    assert evaluation.criteria[0].score == 0
    assert evaluation.overall_score == 0


def test_a_rubric_without_criteria_never_passes() -> None:
    """Scenario: A criterion below its threshold is flagged."""
    evaluation = build_rubric_evaluation(
        CarouselRubric(id="empty", name="Empty", criteria=()), []
    )
    assert (evaluation.overall_score, evaluation.passed) == (0, False)


def test_a_negative_weight_counts_as_one() -> None:
    """Scenario: The drafted carousel is scored on 0-100 per criterion."""
    rubric = CarouselRubric(
        id="w",
        name="W",
        criteria=(_criterion("clarity", 0.5, -3.0), _criterion("hook", 0.5)),
    )
    evaluation = build_rubric_evaluation(
        rubric, [JudgedCriterion("clarity", 100), JudgedCriterion("hook", 0)]
    )
    assert evaluation.overall_score == 50
