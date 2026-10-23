"""A carousel's quality rubric and its scores (0-100 per criterion)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Self, TypeVar

from rag_backend.domain.models.rubric import RubricCriterion


@dataclass(frozen=True)
class CarouselRubric:
    """The rubric a carousel is drafted and scored against."""

    id: str
    name: str
    criteria: tuple[RubricCriterion, ...]
    version: int = 1


@dataclass(frozen=True)
class CriterionScore:
    """One criterion's 0-100 score against its 0-100 threshold.

    ``description``, ``scale`` and ``weight`` are the criterion as it was when it
    was scored, so a later rubric edit never re-reads an old score.
    """

    criterion_id: str
    name: str
    score: int
    threshold: int
    passed: bool
    feedback: str = ""
    description: str = ""
    scale: str = ""
    weight: float = 1.0


@dataclass(frozen=True)
class CarouselRubricEvaluation:
    """Every criterion's score, the weighted 0-100 overall and the verdict.

    ``rubric_version`` is the version of the rubric the scores were given under.
    """

    rubric_id: str
    rubric_name: str
    overall_score: int
    passed: bool
    criteria: tuple[CriterionScore, ...]
    feedback: str = ""
    rubric_version: int = 1

    def to_state(self) -> dict[str, object]:
        """The ``rubric_scores`` shape the final review renders."""
        return {
            "rubric_id": self.rubric_id,
            "rubric_name": self.rubric_name,
            "rubric_version": self.rubric_version,
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
                    "description": c.description,
                    "scale": c.scale,
                    "weight": c.weight,
                }
                for c in self.criteria
            ],
        }

    def criterion_rows(self) -> dict[str, dict[str, object]]:
        """Per-criterion scores keyed by id, for ``rubric_evaluation_scores.scores``.

        Each row carries the criterion as scored and the rubric version.
        """
        return {
            c.criterion_id: {
                "name": c.name,
                "score": c.score,
                "threshold": c.threshold,
                "passed": c.passed,
                "description": c.description,
                "scale": c.scale,
                "weight": c.weight,
                "rubric_version": self.rubric_version,
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


class RubricScopedAgent(Protocol):
    """An agent that can draft against a carousel's quality rubric."""

    def with_rubric(self, rubric: CarouselRubric | None) -> Self:
        """This agent drafting against ``rubric``."""
        ...


AgentT = TypeVar("AgentT", bound=RubricScopedAgent)


def agent_for_rubric(agent: AgentT, rubric: CarouselRubric | None) -> AgentT:
    """``agent`` drafting against ``rubric``; no rubric leaves it untouched."""
    return agent if rubric is None else agent.with_rubric(rubric)


__all__ = [
    "AgentT",
    "CarouselRubric",
    "CarouselRubricEvaluation",
    "CriterionScore",
    "JudgedCriterion",
    "RubricJudgeRequest",
    "RubricScopedAgent",
    "agent_for_rubric",
]
