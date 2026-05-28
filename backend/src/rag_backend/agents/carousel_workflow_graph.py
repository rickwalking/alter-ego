"""Carousel workflow graph wiring and routing."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from rag_backend.agents.carousel_workflow_nodes import (
    brief_phase,
    content_phase_async,
    design_phase_async,
    final_review_phase,
    images_phase_async,
    outline_phase_async,
    research_phase,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    SEND_BACK_TARGET_PHASE_KEY,
)

_ROUTE_APPROVED = "approved"
_ROUTE_RETRY = "retry"

_PHASE_APPROVAL_FIELDS: dict[str, str] = {
    PHASE_RESEARCH: "research_approved",
    PHASE_OUTLINE: "outline_approved",
    PHASE_CONTENT: "content_approved",
    PHASE_DESIGN: "design_approved",
    PHASE_IMAGES: "images_approved",
    PHASE_FINAL_REVIEW: "quality_passed",
}


def route_after_gate(state: CarouselWorkflowState, approved_field: str) -> str:
    if state.get(approved_field):
        return _ROUTE_APPROVED
    return _ROUTE_RETRY


def needs_gate_reopen(snapshot: object) -> bool:
    """Detect workflows stuck at END while still awaiting human review."""
    next_nodes = getattr(snapshot, "next", ()) or ()
    if next_nodes:
        return False
    values = getattr(snapshot, "values", None)
    if not isinstance(values, dict):
        return False
    phase_status = str(values.get("phase_status", ""))
    if phase_status != PHASE_STATUS_AWAITING_HUMAN:
        return False
    phase = str(values.get("current_phase", ""))
    if not phase or phase == PHASE_PUBLISHED:
        return False
    approved_field = _PHASE_APPROVAL_FIELDS.get(phase)
    return not (approved_field and values.get(approved_field))


def route_after_final_review(state: CarouselWorkflowState) -> str:
    if state.get("quality_passed"):
        return _ROUTE_APPROVED
    target = state.get(SEND_BACK_TARGET_PHASE_KEY)
    if isinstance(target, str) and target in {
        PHASE_RESEARCH,
        PHASE_OUTLINE,
        PHASE_CONTENT,
        PHASE_DESIGN,
        PHASE_IMAGES,
    }:
        return target
    return _ROUTE_RETRY


def build_carousel_workflow_graph() -> StateGraph:
    """Build the 7-phase carousel workflow graph."""
    graph = StateGraph(CarouselWorkflowState)
    graph.add_node(PHASE_BRIEF, brief_phase)
    graph.add_node(PHASE_RESEARCH, research_phase)
    graph.add_node(PHASE_OUTLINE, outline_phase_async)
    graph.add_node(PHASE_CONTENT, content_phase_async)
    graph.add_node(PHASE_DESIGN, design_phase_async)
    graph.add_node(PHASE_IMAGES, images_phase_async)
    graph.add_node(PHASE_FINAL_REVIEW, final_review_phase)

    graph.set_entry_point(PHASE_BRIEF)
    graph.add_edge(PHASE_BRIEF, PHASE_RESEARCH)
    graph.add_conditional_edges(
        PHASE_RESEARCH,
        lambda state: route_after_gate(state, "research_approved"),
        {_ROUTE_APPROVED: PHASE_OUTLINE, _ROUTE_RETRY: PHASE_RESEARCH},
    )
    graph.add_conditional_edges(
        PHASE_OUTLINE,
        lambda state: route_after_gate(state, "outline_approved"),
        {_ROUTE_APPROVED: PHASE_CONTENT, _ROUTE_RETRY: PHASE_OUTLINE},
    )
    graph.add_conditional_edges(
        PHASE_CONTENT,
        lambda state: route_after_gate(state, "content_approved"),
        {_ROUTE_APPROVED: PHASE_DESIGN, _ROUTE_RETRY: PHASE_CONTENT},
    )
    graph.add_conditional_edges(
        PHASE_DESIGN,
        lambda state: route_after_gate(state, "design_approved"),
        {_ROUTE_APPROVED: PHASE_IMAGES, _ROUTE_RETRY: PHASE_DESIGN},
    )
    graph.add_conditional_edges(
        PHASE_IMAGES,
        lambda state: route_after_gate(state, "images_approved"),
        {_ROUTE_APPROVED: PHASE_FINAL_REVIEW, _ROUTE_RETRY: PHASE_IMAGES},
    )
    graph.add_conditional_edges(
        PHASE_FINAL_REVIEW,
        route_after_final_review,
        {
            _ROUTE_APPROVED: END,
            _ROUTE_RETRY: PHASE_FINAL_REVIEW,
            PHASE_RESEARCH: PHASE_RESEARCH,
            PHASE_OUTLINE: PHASE_OUTLINE,
            PHASE_CONTENT: PHASE_CONTENT,
            PHASE_DESIGN: PHASE_DESIGN,
            PHASE_IMAGES: PHASE_IMAGES,
        },
    )
    return graph


__all__ = ["build_carousel_workflow_graph", "needs_gate_reopen"]
