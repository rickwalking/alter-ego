"""Schemas for carousel editorial workflow API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from rag_backend.domain.constants.carousel_presentation import SEVERITY_BLOCKER
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_DOCUMENT

ReviewAction = Literal["approve", "reject", "revise", "edit"]


class EditorialSourceInput(BaseModel):
    """Source material for editorial workflow."""

    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    source_type: str = SOURCE_TYPE_DOCUMENT


class EditorialWorkflowStartRequest(BaseModel):
    """Request body to start the 7-phase editorial workflow."""

    topic: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    brief: str = Field(..., min_length=1)
    sources: list[EditorialSourceInput] = Field(default_factory=list)
    persona_id: str | None = None
    reviewer_id: str | None = None


class LocalizedSlideReview(BaseModel):
    """Bilingual slide copy exposed at content review."""

    slide_index: int
    slide_type: str
    presentation_pt: dict[str, object] = Field(default_factory=dict)
    presentation_en: dict[str, object] = Field(default_factory=dict)


class EditorialStructuredFeedback(BaseModel):
    """Phase-specific structured feedback for workflow resume (CP-019)."""

    target_phase: str | None = None
    edited_text: str | None = None
    edited_localized_slides: list[LocalizedSlideReview] | None = None


class EditorialWorkflowResumeRequest(BaseModel):
    """Human review response for workflow resume."""

    action: ReviewAction
    feedback: str | None = None
    expected_version: int = Field(..., ge=1)
    structured_feedback: EditorialStructuredFeedback | None = None


class EditorialWorkflowResumeAcceptedResponse(BaseModel):
    """Immediate acknowledgement for async workflow resume (RW-010)."""

    accepted: bool = True
    project_id: str
    current_phase: str
    phase_status: str
    lock_version: int


class SlideValidationViolationResponse(BaseModel):
    """One deterministic presentation validation violation."""

    code: str
    message: str
    slide_index: int | None = None
    locale: str | None = None
    field: str | None = None
    # AE-0312: severity tier ("blocker" | "warning"); defaults to blocker so a
    # legacy report without the field keeps its blocking treatment client-side.
    severity: str = SEVERITY_BLOCKER


class SlideValidationReportResponse(BaseModel):
    """Aggregated presentation validation report for content review."""

    validation_status: str
    validated_at: str
    blocking: bool
    violations: list[SlideValidationViolationResponse] = Field(default_factory=list)


class SlideImagePrompt(BaseModel):
    """Image-generation prompt preview for one carousel slide."""

    slide_index: int
    title: str
    image_prompt: str
    rendered_image_prompt: str | None = None
    image_generation_key: str | None = None
    image_prompt_hash: str | None = None
    image_provider: str | None = None
    image_model: str | None = None
    image_style: str | None = None
    theme_name: str | None = None
    theme_colors: dict[str, str] | None = None


class EditorialWorkflowStateResponse(BaseModel):
    """Current workflow state returned to clients."""

    project_id: str
    current_phase: str
    phase_status: str
    research_findings: list[dict[str, object]] = Field(default_factory=list)
    outline: list[dict[str, object]] = Field(default_factory=list)
    slide_drafts: list[dict[str, object]] = Field(default_factory=list)
    image_assets: list[str] = Field(default_factory=list)
    design_applied: bool = False
    phase_progress: dict[str, object] | None = None
    status: str = "draft"
    lock_version: int = 1
    workflow_status: str = ""
    persona_scores: dict[str, object] = Field(default_factory=dict)
    caption: str | None = None
    blog_markdown: str | None = None
    linkedin_post_pt: str | None = None
    linkedin_post_en: str | None = None
    rubric_scores: dict[str, object] = Field(default_factory=dict)
    phase_feedback: dict[str, list[str]] = Field(default_factory=dict)
    revision_count: dict[str, int] = Field(default_factory=dict)
    error_message: str | None = None
    slide_image_prompts: list[SlideImagePrompt] | None = None
    presentation_policy_version: str | None = None
    localized_slides: list[LocalizedSlideReview] = Field(default_factory=list)
    presentation_validation: SlideValidationReportResponse | None = None
    # AE-0309: fail-closed content-gate report; present only when the content
    # build's validate -> repair -> retry chain still ended blocking.
    content_gate_validation: SlideValidationReportResponse | None = None
    # AE-0310: client-displayable recovery-hint code set while the design step
    # holds a blocking validation report (direct edits or a content send-back
    # resolve violations; a plain revise does not modify content).
    design_recovery_hint: str | None = None
    # AE-0315: run metadata, populated ONLY while phase_status == in_progress
    # so the create flow reconstructs the in-progress banner on reload without
    # depending on having witnessed the run.started SSE event.
    run_started_at: datetime | None = None
    run_stage: str | None = None


__all__ = [
    "EditorialSourceInput",
    "EditorialStructuredFeedback",
    "EditorialWorkflowResumeAcceptedResponse",
    "EditorialWorkflowResumeRequest",
    "EditorialWorkflowStartRequest",
    "EditorialWorkflowStateResponse",
    "LocalizedSlideReview",
    "ReviewAction",
    "SlideImagePrompt",
    "SlideValidationReportResponse",
    "SlideValidationViolationResponse",
]
