"""A carousel's quality rubric and its scores (0-100 per criterion)."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.domain.models.rubric import RubricCriterion


@dataclass(frozen=True)
class CarouselRubric:
    """The rubric a carousel is drafted and scored against."""

    id: str
    name: str
    criteria: tuple[RubricCriterion, ...]


@dataclass(frozen=True)
class CriterionScore:
    """One criterion's 0-100 score against its 0-100 threshold."""

    criterion_id: str
    name: str
    score: int
    threshold: int
    passed: bool
    feedback: str = ""


@dataclass(frozen=True)
class CarouselRubricEvaluation:
    """Every criterion's score, the weighted 0-100 overall and the verdict."""

    rubric_id: str
    rubric_name: str
    overall_score: int
    passed: bool
    criteria: tuple[CriterionScore, ...]
    feedback: str = ""

    def to_state(self) -> dict[str, object]:
        """The ``rubric_scores`` shape the final review renders."""
        return {
            "rubric_id": self.rubric_id,
            "rubric_name": self.rubric_name,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "feedback": self.feedback,
            "criteria": [
                {
                    "id": c.criterion_id,
                    "name": c.name,
                    "score": c.score,
                    "threshold": c.threshold,
                    "passed": c.passed,
                    "feedback": c.feedback,
                }
                for c in self.criteria
            ],
        }

    def criterion_rows(self) -> dict[str, dict[str, object]]:
        """Per-criterion scores keyed by id, for ``rubric_evaluation_scores.scores``."""
        return {
            c.criterion_id: {
                "name": c.name,
                "score": c.score,
                "threshold": c.threshold,
                "passed": c.passed,
            }
            for c in self.criteria
        }


@dataclass(frozen=True)
class RubricJudgeRequest:
    """Score ``content`` (the carousel's slides, in order) against ``rubric``."""

    rubric: CarouselRubric
    content: str
    project_id: str = ""


@dataclass(frozen=True)
class JudgedCriterion:
    """What the judge said about one criterion (score as answered)."""

    criterion_id: str
    score: float
    feedback: str = ""


__all__ = [
    "CarouselRubric",
    "CarouselRubricEvaluation",
    "CriterionScore",
    "JudgedCriterion",
    "RubricJudgeRequest",
]
