"""Schemas for carousel editorial workflow API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EditorialSourceInput(BaseModel):
    """Source material for editorial workflow."""

    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    source_type: str = "document"


class EditorialWorkflowStartRequest(BaseModel):
    """Request body to start the 7-phase editorial workflow."""

    topic: str = Field(..., min_length=1)
    audience: str = Field(..., min_length=1)
    brief: str = Field(..., min_length=1)
    sources: list[EditorialSourceInput] = Field(default_factory=list)
    persona_id: str | None = None
    reviewer_id: str | None = None


class EditorialWorkflowResumeRequest(BaseModel):
    """Human review response for workflow resume."""

    action: str = Field(..., min_length=1)
    feedback: str | None = None


class EditorialWorkflowStateResponse(BaseModel):
    """Current workflow state returned to clients."""

    project_id: str
    current_phase: str
    phase_status: str
    research_findings: list[dict[str, object]] = Field(default_factory=list)
    outline: list[dict[str, object]] = Field(default_factory=list)
    slide_drafts: list[dict[str, object]] = Field(default_factory=list)
    status: str = "draft"


__all__ = [
    "EditorialSourceInput",
    "EditorialWorkflowResumeRequest",
    "EditorialWorkflowStartRequest",
    "EditorialWorkflowStateResponse",
]
