"""Shared dataclasses for editorial workflow."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    DEFAULT_CONTENT_DRAFT_CONCURRENCY,
)
from rag_backend.domain.constants.content_feedback import FEEDBACK_SOURCE_HUMAN
from rag_backend.domain.models.persona import PersonaProfile


@dataclass(frozen=True)
class ChatModelRoles:
    """AE-0391: the chat model of each carousel task role + drafting bound."""

    reasoning: BaseChatModel
    fast: BaseChatModel
    # Slides drafted (and persona-scored) concurrently in the content phase.
    draft_concurrency: int = DEFAULT_CONTENT_DRAFT_CONCURRENCY

    @classmethod
    def coerce(cls, llm: BaseChatModel | ChatModelRoles) -> ChatModelRoles:
        """A single model serves both roles (tests, legacy callers)."""
        if isinstance(llm, ChatModelRoles):
            return llm
        return cls(reasoning=llm, fast=llm)


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
    """Inputs for persisting reviewer phase feedback.

    ``count_revision=False`` stores the note without bumping the phase's
    revision counter (AE-0310): edited-slides submissions and a plain design
    revise while a blocking report exists are provable non-regenerations, so
    they must not consume the LLM revision budget.
    """

    project_id: str
    prior: CarouselWorkflowState
    feedback: str | None
    target_phase: str | None = None
    count_revision: bool = True
    # AE-0405: who wrote the note (human reviewer or the autopilot gate).
    source: str = FEEDBACK_SOURCE_HUMAN


__all__ = [
    "EditorialWorkflowStartInput",
    "PhaseFeedbackPersistParams",
    "ResumeWorkflowInput",
    "ReviewEventEmitContext",
]
