"""Unit tests for carousel workflow engine.

Feature: 7-phase carousel editorial workflow with human gates
"""

from typing import cast
from unittest.mock import patch

import pytest

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.carousel_workflow_graph import build_carousel_workflow_graph
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_FINAL_REVIEW,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    REVIEW_ACTION_APPROVE,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
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
        """Given approved reviews, when workflow runs, then it reaches approved_for_publish."""
        engine = CarouselWorkflowEngine()

        with patch(
            "rag_backend.agents.carousel_workflow_nodes.interrupt",
            return_value={"action": REVIEW_ACTION_APPROVE},
        ):
            state = await engine.start("project-1", {"topic": "Security"})

        assert state["research_approved"] is True
        assert state["quality_passed"] is True
        assert state["current_phase"] == PHASE_FINAL_REVIEW
        assert state["workflow_status"] == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        assert state["status"] == "draft"

    @pytest.mark.asyncio
    async def test_start_stays_on_research_when_rejected(self) -> None:
        """Given rejected research review, when resumed, then phase stays on research."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "project-2"
                await engine.start(
                    project_id,
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                paused = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert paused.next == (PHASE_RESEARCH,)

                state = await engine.resume(
                    project_id,
                    {"action": "reject", "feedback": "needs more sources"},
                )

                assert state["research_approved"] is False
                assert state["current_phase"] == PHASE_RESEARCH
                snapshot = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert snapshot.next == (PHASE_RESEARCH,)

    @pytest.mark.asyncio
    async def test_reject_then_approve_advances_to_outline(self) -> None:
        """Given reject then approve, when resumed twice, then outline gate opens."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "project-3"
                await engine.start(
                    project_id,
                    {"topic": "Security"},
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                paused = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert paused.next == (PHASE_RESEARCH,)

                await engine.resume(
                    project_id,
                    {"action": "reject", "feedback": "more detail"},
                )
                after_reject = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert after_reject.next == (PHASE_RESEARCH,)

                state = await engine.resume(
                    project_id,
                    {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                )

                assert state["research_approved"] is True
                resumed = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert resumed.next == (PHASE_OUTLINE,)

    @pytest.mark.asyncio
    async def test_resume_reopens_stuck_end_gate(self) -> None:
        """Given reject on research, when approving, then workflow advances to outline."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "stuck-project"
                await engine.start(
                    project_id,
                    {"topic": "AI"},
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                await engine.resume(project_id, {"action": "reject"})
                snapshot = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert snapshot.next == (PHASE_RESEARCH,)

                state = await engine.resume(
                    project_id,
                    {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                )

                assert state["research_approved"] is True
                snapshot_after = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert snapshot_after.next == (PHASE_OUTLINE,)

    def test_merge_interrupt_review_payload_exposes_gate_artifacts(self) -> None:
        """Given pending interrupt payload, when merging state, then review data is visible."""
        from types import SimpleNamespace

        outline = [{"slide_index": 1, "title": "Hook", "key_points": ["A"]}]
        state: dict[str, object] = {"outline": [], "research_findings": []}
        snapshot = SimpleNamespace(
            interrupts=(
                SimpleNamespace(
                    value={
                        "phase": PHASE_OUTLINE,
                        "findings": [{"source": "report", "key_points": ["risk"]}],
                        "outline": outline,
                    }
                ),
            ),
            tasks=(),
        )

        CarouselWorkflowEngine._merge_interrupt_review_payload(
            cast("CarouselWorkflowState", state),
            snapshot,
        )

        assert state["outline"] == outline
        assert state["research_findings"] == [
            {"source": "report", "key_points": ["risk"]}
        ]
