"""Pydantic schemas for Persona and Rubric management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


class PersonaProfileListResponse(BaseModel):
    """Schema for listing persona profiles."""
    items: list[PersonaProfileResponse]
    total: int


class RubricCriterion(BaseModel):
    """Schema for a rubric criterion."""
    id: str
    name: str
    description: str
    weight: Annotated[float, Field(ge=0.0, le=1.0)]
    evaluation_method: str  # "ai_auto" | "human_required" | "hybrid"
    min_threshold: Annotated[float, Field(ge=0.0, le=1.0)]
    scoring_scale: str  # "1-10" | "pass_fail" | "grade_a_f" | "0-100"
    prompt_template: str


class QualityRubricCreate(BaseModel):
    """Schema for creating a quality rubric."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    criteria: list[RubricCriterion] = Field(default_factory=list)
    applicable_content_types: list[str] = Field(default_factory=lambda: ["carousel"])
    is_default: bool = False


class QualityRubricUpdate(BaseModel):
    """Schema for updating a quality rubric."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    criteria: list[RubricCriterion] | None = None
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

    class Config:
        from_attributes = True


class QualityRubricListResponse(BaseModel):
    """Schema for listing quality rubrics."""
    items: list[QualityRubricResponse]
    total: int


class RubricEvaluationScore(BaseModel):
    """Schema for rubric evaluation score."""
    criterion_id: str
    score: Annotated[float, Field(ge=0.0, le=1.0)]
    weight: Annotated[float, Field(ge=0.0, le=1.0)]
    passed: bool


class RubricEvaluationResponse(BaseModel):
    """Schema for rubric evaluation response."""
    rubric_id: UUID
    content_id: UUID
    content_type: str
    evaluated_at: datetime
    scores: dict[str, RubricEvaluationScore]
    overall_score: Annotated[float, Field(ge=0.0, le=1.0)]
    passed: bool
    feedback: list[dict]


__all__ = [
    "PersonaProfileCreate",
    "PersonaProfileUpdate",
    "PersonaProfileResponse",
    "PersonaProfileListResponse",
    "ToneAttributes",
    "QualityRubricCreate",
    "QualityRubricUpdate",
    "QualityRubricResponse",
    "QualityRubricListResponse",
    "RubricCriterion",
    "RubricEvaluationScore",
    "RubricEvaluationResponse",
]