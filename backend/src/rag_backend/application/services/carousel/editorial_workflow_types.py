"""Shared dataclasses for editorial workflow."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.models.persona import PersonaProfile


@dataclass(frozen=True)
class ResumeWorkflowInput:
    """Inputs required to resume a workflow after human review."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None = None
    db: AsyncSession | None = None
    persona: PersonaProfile | None = None
    project_title: str = ""
    structured_feedback: dict[str, object] | None = None


@dataclass(frozen=True)
class EditorialWorkflowStartInput:
    """Inputs required to start the editorial workflow."""

    topic: str
    audience: str
    brief: str
    sources: list[dict[str, str]]
    persona: PersonaProfile | None = None
    user_id: str = "system"
    reviewer_id: str | None = None


@dataclass(frozen=True)
class ReviewEventEmitContext:
    """Parameters for emitting carousel review workflow events."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None
    prior: CarouselWorkflowState | None
    state: CarouselWorkflowState


@dataclass(frozen=True)
class PhaseFeedbackPersistParams:
    """Inputs for persisting reviewer phase feedback."""

    project_id: str
    prior: CarouselWorkflowState
    feedback: str | None
    target_phase: str | None = None


__all__ = [
    "EditorialWorkflowStartInput",
    "PhaseFeedbackPersistParams",
    "ResumeWorkflowInput",
    "ReviewEventEmitContext",
]
