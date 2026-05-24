"""Unit tests for carousel workflow engine.

Feature: 7-phase carousel editorial workflow with human gates
"""

from unittest.mock import patch

import pytest

from rag_backend.agents.carousel_workflow import (
    CarouselWorkflowEngine,
    build_carousel_workflow_graph,
)
from rag_backend.application.services.carousel.workflow_state import get_initial_carousel_state
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    REVIEW_ACTION_APPROVE,
)


class TestCarouselWorkflowState:
    """Tests for workflow state helpers."""

    def test_initial_state_defaults(self) -> None:
        """Given project id, when creating initial state, then brief phase is set."""
        state = get_initial_carousel_state("project-1", {"topic": "AI"})

        assert state["project_id"] == "project-1"
        assert state["current_phase"] == PHASE_BRIEF
        assert state["brief"] == {"topic": "AI"}
        assert state["brief_approved"] is False


class TestCarouselWorkflowGraph:
    """Tests for LangGraph workflow construction."""

    def test_graph_builds_all_phase_nodes(self) -> None:
        """Given builder, when graph is created, then all phase nodes exist."""
        graph = build_carousel_workflow_graph()

        assert PHASE_BRIEF in graph.nodes
        assert PHASE_RESEARCH in graph.nodes
        assert PHASE_OUTLINE in graph.nodes


class TestCarouselWorkflowEngine:
    """Tests for workflow execution with interrupts."""

    @pytest.mark.asyncio
    async def test_start_completes_when_all_reviews_approve(self) -> None:
        """Given approved reviews, when workflow runs, then it reaches published state."""
        engine = CarouselWorkflowEngine()

        with patch(
            "rag_backend.agents.carousel_workflow.interrupt",
            return_value={"action": REVIEW_ACTION_APPROVE},
        ):
            state = await engine.start("project-1", {"topic": "Security"})

        assert state["research_approved"] is True
        assert state["quality_passed"] is True
        assert state["current_phase"] == PHASE_PUBLISHED

    @pytest.mark.asyncio
    async def test_start_stays_on_research_when_rejected(self) -> None:
        """Given rejected research review, when resumed, then phase stays on research."""
        engine = CarouselWorkflowEngine()

        with patch(
            "rag_backend.agents.carousel_workflow.interrupt",
            return_value={"action": "reject"},
        ):
            state = await engine.start("project-2")

        assert state["research_approved"] is False
        assert state["current_phase"] == PHASE_RESEARCH
