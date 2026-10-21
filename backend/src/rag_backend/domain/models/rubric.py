"""Domain models for Quality Rubrics and Evaluation Criteria."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypedDict
from uuid import UUID, uuid4

from rag_backend.domain.clock import utc_now


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
    criteria: list[RubricCriterion] = field(default_factory=list)
    applicable_content_types: list[str] = field(default_factory=lambda: ["carousel"])
    is_default: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    version: int = 1


@dataclass
class RubricEvaluationScore:
    """Result of evaluating content against a rubric."""

    rubric_id: UUID
    content_id: UUID
    content_type: str
    evaluated_at: datetime = field(default_factory=utc_now)
    scores: dict[str, dict[str, float | bool]] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    feedback: list[dict[str, object]] = field(default_factory=list)
