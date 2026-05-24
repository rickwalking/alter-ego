"""LangGraph carousel workflow with human-in-the-loop approval gates."""

from __future__ import annotations

from typing import cast

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
    INTERRUPT_TYPE_DESIGN_REVIEW,
    INTERRUPT_TYPE_FINAL_REVIEW,
    INTERRUPT_TYPE_IMAGE_REVIEW,
    INTERRUPT_TYPE_OUTLINE_REVIEW,
    INTERRUPT_TYPE_RESEARCH_REVIEW,
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
)

_ROUTE_APPROVED = "approved"
_ROUTE_RETRY = "retry"


def _await_human_review(
    state: CarouselWorkflowState,
    phase: str,
    interrupt_type: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Pause workflow until a human reviewer responds."""
    review = interrupt(
        {
            "type": interrupt_type,
            "phase": phase,
            "project_id": state.get("project_id"),
            **payload,
        }
    )
    if not isinstance(review, dict):
        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
    if review.get("action") == REVIEW_ACTION_APPROVE:
        return {"phase_status": PHASE_STATUS_APPROVED}
    return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}


def brief_phase(_state: CarouselWorkflowState) -> dict[str, object]:
    """Validate brief and move to research."""
    return {
        "current_phase": PHASE_RESEARCH,
        "phase_status": PHASE_STATUS_IN_PROGRESS,
        "brief_approved": True,
    }


def research_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Run research then request human review."""
    findings = state.get("research_findings") or []
    review_update = _await_human_review(
        state,
        PHASE_RESEARCH,
        INTERRUPT_TYPE_RESEARCH_REVIEW,
        {"findings": findings, "message": "Review research findings."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "research_approved": approved,
        "current_phase": PHASE_RESEARCH,
    }


def outline_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Generate outline and request human approval."""
    outline = state.get("outline") or []
    review_update = _await_human_review(
        state,
        PHASE_OUTLINE,
        INTERRUPT_TYPE_OUTLINE_REVIEW,
        {"outline": outline, "message": "Review and approve the outline."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "outline_approved": approved,
        "current_phase": PHASE_OUTLINE,
    }


def content_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Draft slide content and request human approval."""
    drafts = state.get("slide_drafts") or []
    review_update = _await_human_review(
        state,
        PHASE_CONTENT,
        INTERRUPT_TYPE_CONTENT_REVIEW,
        {"slide_drafts": drafts, "message": "Review slide copy."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "content_approved": approved,
        "current_phase": PHASE_CONTENT,
    }


def design_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Apply design and request human approval."""
    review_update = _await_human_review(
        state,
        PHASE_DESIGN,
        INTERRUPT_TYPE_DESIGN_REVIEW,
        {"design_applied": state.get("design_applied", False), "message": "Review design."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "design_applied": True,
        "design_approved": approved,
        "current_phase": PHASE_DESIGN,
    }


def images_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Generate images and request human approval."""
    assets = state.get("image_assets") or []
    review_update = _await_human_review(
        state,
        PHASE_IMAGES,
        INTERRUPT_TYPE_IMAGE_REVIEW,
        {"image_assets": assets, "message": "Review generated images."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "images_approved": approved,
        "current_phase": PHASE_IMAGES,
    }


def final_review_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Final quality gate before publish."""
    review_update = _await_human_review(
        state,
        PHASE_FINAL_REVIEW,
        INTERRUPT_TYPE_FINAL_REVIEW,
        {
            "rubric_scores": state.get("rubric_scores") or {},
            "message": "Final review before publish.",
        },
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "quality_passed": approved,
        "current_phase": PHASE_PUBLISHED if approved else PHASE_FINAL_REVIEW,
        "status": "published" if approved else "draft",
    }


def _route_after_gate(state: CarouselWorkflowState, approved_field: str) -> str:
    if state.get(approved_field):
        return _ROUTE_APPROVED
    return _ROUTE_RETRY


def build_carousel_workflow_graph() -> StateGraph:
    """Build the 7-phase carousel workflow graph."""
    graph = StateGraph(CarouselWorkflowState)
    graph.add_node(PHASE_BRIEF, brief_phase)
    graph.add_node(PHASE_RESEARCH, research_phase)
    graph.add_node(PHASE_OUTLINE, outline_phase)
    graph.add_node(PHASE_CONTENT, content_phase)
    graph.add_node(PHASE_DESIGN, design_phase)
    graph.add_node(PHASE_IMAGES, images_phase)
    graph.add_node(PHASE_FINAL_REVIEW, final_review_phase)

    graph.set_entry_point(PHASE_BRIEF)
    graph.add_edge(PHASE_BRIEF, PHASE_RESEARCH)
    graph.add_conditional_edges(
        PHASE_RESEARCH,
        lambda state: _route_after_gate(state, "research_approved"),
        {_ROUTE_APPROVED: PHASE_OUTLINE, _ROUTE_RETRY: END},
    )
    graph.add_conditional_edges(
        PHASE_OUTLINE,
        lambda state: _route_after_gate(state, "outline_approved"),
        {_ROUTE_APPROVED: PHASE_CONTENT, _ROUTE_RETRY: END},
    )
    graph.add_conditional_edges(
        PHASE_CONTENT,
        lambda state: _route_after_gate(state, "content_approved"),
        {_ROUTE_APPROVED: PHASE_DESIGN, _ROUTE_RETRY: END},
    )
    graph.add_conditional_edges(
        PHASE_DESIGN,
        lambda state: _route_after_gate(state, "design_approved"),
        {_ROUTE_APPROVED: PHASE_IMAGES, _ROUTE_RETRY: END},
    )
    graph.add_conditional_edges(
        PHASE_IMAGES,
        lambda state: _route_after_gate(state, "images_approved"),
        {_ROUTE_APPROVED: PHASE_FINAL_REVIEW, _ROUTE_RETRY: END},
    )
    graph.add_edge(PHASE_FINAL_REVIEW, END)
    return graph


class CarouselWorkflowEngine:
    """Runs the editorial carousel workflow with LangGraph interrupts."""

    def __init__(self, checkpointer: object | None = None) -> None:
        graph = build_carousel_workflow_graph()
        self._app = graph.compile(checkpointer=checkpointer)

    async def start(
        self,
        project_id: str,
        brief: dict[str, object] | None = None,
        **state_overrides: object,
    ) -> CarouselWorkflowState:
        """Start a new workflow run."""
        initial = get_initial_carousel_state(project_id, brief)
        initial.update(state_overrides)
        config = {"configurable": {"thread_id": project_id}}
        result = await self._app.ainvoke(initial, config=config)
        return cast(CarouselWorkflowState, result)

    async def resume(
        self,
        project_id: str,
        human_input: dict[str, object] | None = None,
    ) -> CarouselWorkflowState:
        """Resume a paused workflow after human review."""
        config = {"configurable": {"thread_id": project_id}}
        result = await self._app.ainvoke(human_input, config=config)
        return cast(CarouselWorkflowState, result)

    async def get_state(self, project_id: str) -> CarouselWorkflowState | None:
        """Load persisted workflow state from checkpointer (WF-002)."""
        config = {"configurable": {"thread_id": project_id}}
        snapshot = await self._app.aget_state(config)
        if snapshot is None or snapshot.values is None:
            return None
        values = snapshot.values
        if not isinstance(values, dict):
            return None
        return cast(CarouselWorkflowState, values)


__all__ = ["CarouselWorkflowEngine", "build_carousel_workflow_graph"]
