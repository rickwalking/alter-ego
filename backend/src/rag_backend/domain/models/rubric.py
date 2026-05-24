"""Domain models for Quality Rubrics and Evaluation Criteria."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypedDict
from uuid import UUID, uuid4


class EvaluationMethod(StrEnum):
    """Methods for evaluating rubric criteria."""

    AI_AUTO = "ai_auto"
    HUMAN_REQUIRED = "human_required"
    HYBRID = "hybrid"


class ScoringScale(StrEnum):
    """Scales for scoring rubric criteria."""

    PASS_FAIL = "pass_fail"
    GRADE_A_F = "grade_a_f"
    SCORE_1_10 = "1-10"
    SCORE_0_100 = "0-100"


class RubricCriterion(TypedDict):
    """A single criterion within a quality rubric."""

    id: str
    name: str
    description: str
    weight: float
    evaluation_method: EvaluationMethod
    min_threshold: float
    scoring_scale: ScoringScale
    prompt_template: str


@dataclass
class QualityRubric:
    """Quality rubric for evaluating content."""

    id: UUID = field(default_factory=uuid4)
    name: str = "Instagram Carousel Quality"
    description: str = "Standard quality criteria for Instagram carousels"
    criteria: list[dict] = field(default_factory=list)
    applicable_content_types: list[str] = field(default_factory=lambda: ["carousel"])
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def add_criterion(
        self,
        name: str,
        description: str,
        weight: float,
        evaluation_method: EvaluationMethod,
        min_threshold: float,
        scoring_scale: ScoringScale,
        prompt_template: str,
    ) -> None:
        """Add a criterion to the rubric."""
        criterion: dict = {
            "id": f"{name.lower().replace(' ', '_')}_criterion",
            "name": name,
            "description": description,
            "weight": weight,
            "evaluation_method": evaluation_method,
            "min_threshold": min_threshold,
            "scoring_scale": scoring_scale,
            "prompt_template": prompt_template,
        }
        self.criteria.append(criterion)
        self.updated_at = datetime.utcnow()

    def get_total_weight(self) -> float:
        """Calculate total weight of all criteria."""
        return sum(c["weight"] for c in self.criteria)


@dataclass
class RubricEvaluationScore:
    """Result of evaluating content against a rubric."""

    rubric_id: UUID
    content_id: UUID
    content_type: str
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    scores: dict[str, dict] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    feedback: list[dict] = field(default_factory=list)

    def add_score(self, criterion_id: str, score: float, weight: float, passed: bool) -> None:
        """Add a criterion score."""
        self.scores[criterion_id] = {
            "score": score,
            "weight": weight,
            "passed": passed,
        }

    def set_overall(self, overall_score: float, passed: bool) -> None:
        """Set overall score and pass/fail status."""
        self.overall_score = overall_score
        self.passed = passed
