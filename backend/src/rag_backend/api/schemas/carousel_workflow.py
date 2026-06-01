"""Schemas for carousel editorial workflow API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class EditorialStructuredFeedback(BaseModel):
    """Phase-specific structured feedback for workflow resume (CP-019)."""

    target_phase: str | None = None
    edited_text: str | None = None


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


__all__ = [
    "EditorialSourceInput",
    "EditorialStructuredFeedback",
    "EditorialWorkflowResumeAcceptedResponse",
    "EditorialWorkflowResumeRequest",
    "EditorialWorkflowStartRequest",
    "EditorialWorkflowStateResponse",
    "ReviewAction",
]
