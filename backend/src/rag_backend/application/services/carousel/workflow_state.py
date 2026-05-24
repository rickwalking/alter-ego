"""Extended LangGraph state for the 7-phase carousel editorial workflow."""

from __future__ import annotations

from typing import TypedDict

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_STATUS_PENDING,
)


class CarouselWorkflowState(TypedDict, total=False):
    """State for human-in-the-loop carousel workflow."""

    project_id: str
    current_phase: str
    phase_status: str
    brief: dict[str, object]
    brief_approved: bool
    research_findings: list[dict[str, object]]
    research_notes: str
    research_approved: bool
    outline: list[dict[str, object]]
    outline_approved: bool
    slide_drafts: list[dict[str, object]]
    content_approved: bool
    design_applied: bool
    design_feedback: str
    design_approved: bool
    image_assets: list[str]
    images_approved: bool
    rubric_scores: dict[str, object]
    quality_passed: bool
    status: str


def get_initial_carousel_state(
    project_id: str,
    brief: dict[str, object] | None = None,
) -> CarouselWorkflowState:
    """Build the initial workflow state for a carousel project."""
    return {
        "project_id": project_id,
        "current_phase": PHASE_BRIEF,
        "phase_status": PHASE_STATUS_PENDING,
        "brief": brief or {},
        "brief_approved": False,
        "research_findings": [],
        "research_notes": "",
        "research_approved": False,
        "outline": [],
        "outline_approved": False,
        "slide_drafts": [],
        "content_approved": False,
        "design_applied": False,
        "design_feedback": "",
        "design_approved": False,
        "image_assets": [],
        "images_approved": False,
        "rubric_scores": {},
        "quality_passed": False,
        "status": "draft",
    }


__all__ = ["CarouselWorkflowState", "get_initial_carousel_state"]
