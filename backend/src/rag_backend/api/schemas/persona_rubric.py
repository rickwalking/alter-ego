"""Pydantic schemas for Persona and Rubric management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.domain.constants.carousel_rubric import (
    RUBRIC_CRITERION_NAME_MAX_CHARS,
    RUBRIC_CRITERION_TEXT_MAX_CHARS,
    RUBRIC_MAX_CRITERIA,
)
from rag_backend.domain.rubric_scoring import normalize_stored_criterion


class ToneAttributes(BaseModel):
    """Tone attributes for persona voice profile."""

    formal: Annotated[float, Field(ge=0.0, le=1.0)] = 0.3
    conversational: Annotated[float, Field(ge=0.0, le=1.0)] = 0.8
    humorous: Annotated[float, Field(ge=0.0, le=1.0)] = 0.4


class PersonaProfileCreate(BaseModel):
    """Schema for creating a persona profile."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tone_attributes: ToneAttributes | None = None
    writing_samples: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    preferred_phrases: list[str] = Field(default_factory=list)
    sentence_structure_preferences: str | None = None
    paragraph_style: str | None = None
    opinion_expression: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)


class PersonaProfileUpdate(BaseModel):
    """Schema for updating a persona profile."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tone_attributes: ToneAttributes | None = None
    writing_samples: list[str] | None = None
    forbidden_phrases: list[str] | None = None
    preferred_phrases: list[str] | None = None
    sentence_structure_preferences: str | None = None
    paragraph_style: str | None = None
    opinion_expression: str | None = None
    expertise_areas: list[str] | None = None


class PersonaProfileResponse(BaseModel):
    """Schema for persona profile response."""

    id: UUID
    name: str
    description: str | None = None
    tone_attributes: ToneAttributes
    writing_samples: list[str]
    forbidden_phrases: list[str]
    preferred_phrases: list[str]
    sentence_structure_preferences: str | None = None
    paragraph_style: str | None = None
    opinion_expression: str | None = None
    expertise_areas: list[str]
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = ConfigDict(from_attributes=True)


class PersonaProfileListResponse(BaseModel):
    """Schema for listing persona profiles."""

    items: list[PersonaProfileResponse]
    total: int


class RubricCriterion(BaseModel):
    """Schema for a rubric criterion.

    evaluation_method is "ai_auto", "human_required" or "hybrid"; scoring_scale is
    "1-10", "pass_fail", "grade_a_f" or "0-100".
    """

    id: str
    name: str
    description: str
    weight: Annotated[float, Field(ge=0.0, le=1.0)]
    evaluation_method: str
    min_threshold: Annotated[float, Field(ge=0.0, le=1.0)]
    scoring_scale: str
    prompt_template: str


class RubricCriterionInput(RubricCriterion):
    """A criterion as created or updated: bounded text (it reaches LLM prompts).

    Reads keep the plain ``RubricCriterion`` so rubrics stored before the bounds
    still load.
    """

    name: str = Field(..., min_length=1, max_length=RUBRIC_CRITERION_NAME_MAX_CHARS)
    description: str = Field(..., max_length=RUBRIC_CRITERION_TEXT_MAX_CHARS)
    prompt_template: str = Field(..., max_length=RUBRIC_CRITERION_TEXT_MAX_CHARS)


class QualityRubricCreate(BaseModel):
    """Schema for creating a quality rubric."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    criteria: list[RubricCriterionInput] = Field(
        ..., min_length=1, max_length=RUBRIC_MAX_CRITERIA
    )
    applicable_content_types: list[str] = Field(default_factory=lambda: ["carousel"])
    is_default: bool = False


class QualityRubricUpdate(BaseModel):
    """Schema for updating a quality rubric."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    criteria: (
        Annotated[
            list[RubricCriterionInput],
            Field(min_length=1, max_length=RUBRIC_MAX_CRITERIA),
        ]
        | None
    ) = None
    applicable_content_types: list[str] | None = None
    is_default: bool | None = None


class QualityRubricResponse(BaseModel):
    """Schema for quality rubric response."""

    id: UUID
    name: str
    description: str | None = None
    criteria: list[RubricCriterion]
    applicable_content_types: list[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = ConfigDict(from_attributes=True)

    @field_validator("criteria", mode="before")
    @classmethod
    def _stored_thresholds_read_as_fractions(cls, value: object) -> object:
        """A stored legacy threshold (70.0 on 0-100) reads as its fraction (0.7)."""
        if not isinstance(value, list):
            return value
        return [
            normalize_stored_criterion(item) if isinstance(item, dict) else item
            for item in value
        ]


class QualityRubricListResponse(BaseModel):
    """Schema for listing quality rubrics."""

    items: list[QualityRubricResponse]
    total: int


class RubricEvaluationScore(BaseModel):
    """Schema for rubric evaluation score."""

    criterion_id: str
    score: Annotated[float, Field(ge=0.0, le=100.0)]
    weight: Annotated[float, Field(ge=0.0, le=1.0)]
    passed: bool


class RubricEvaluationRequest(BaseModel):
    """Request body for rubric content evaluation."""

    content_type: str = Field(..., min_length=1, max_length=100)
    content_text: str = Field(..., min_length=1, max_length=10000)
    sources: list[str] = Field(default_factory=list)


class RubricEvaluationResponse(BaseModel):
    """Schema for rubric evaluation response."""

    rubric_id: UUID
    content_id: UUID
    content_type: str
    evaluated_at: datetime
    scores: dict[str, RubricEvaluationScore]
    overall_score: Annotated[float, Field(ge=0.0, le=100.0)]
    passed: bool
    feedback: list[dict]


class VoiceScoreRequest(BaseModel):
    """Request body for persona voice match scoring."""

    text: str = Field(..., min_length=1, max_length=10000)


class VoiceScoreResponse(BaseModel):
    """Persona voice match scoring result."""

    tone_match: float
    sentence_structure_match: float
    opinion_strength: float
    originality: float
    human_authenticity: float
    overall: float
    suggestions: list[str] = Field(default_factory=list)
    passed: bool


__all__ = [
    "PersonaProfileCreate",
    "PersonaProfileListResponse",
    "PersonaProfileResponse",
    "PersonaProfileUpdate",
    "QualityRubricCreate",
    "QualityRubricListResponse",
    "QualityRubricResponse",
    "QualityRubricUpdate",
    "RubricCriterion",
    "RubricEvaluationRequest",
    "RubricEvaluationResponse",
    "RubricEvaluationScore",
    "ToneAttributes",
    "VoiceScoreRequest",
    "VoiceScoreResponse",
]
