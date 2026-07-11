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

    @pytest.mark.asyncio
    async def test_paused_final_review_send_back_routes_to_content(self) -> None:
        """AE-0288: from a carousel paused at the final-review gate, a revise with
        structured_feedback.target_phase=content routes the workflow back into the
        content phase (the reliable, supported send-back path).

        NB: this works because the graph is genuinely suspended at final_review's
        interrupt. Re-driving a *terminated* (already-approved) graph is NOT
        reliably supported by LangGraph and is intentionally not attempted here.
        """
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        from rag_backend.domain.constants.carousel_workflow import (
            PHASE_CONTENT,
            PHASE_STATUS_AWAITING_HUMAN,
            REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY,
            STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
        )

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "send-back-paused"
                config = {"configurable": {"thread_id": project_id}}
                await engine.start(
                    project_id,
                    {"topic": "AI"},
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                # Approve research, outline, content, design, images -> the graph
                # pauses awaiting human review at the final_review gate.
                for _ in range(5):
                    await engine.resume(
                        project_id,
                        {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                    )
                paused = await engine._app.aget_state(config)
                assert paused.next == (PHASE_FINAL_REVIEW,)

                await engine.resume(
                    project_id,
                    {
                        "action": REVIEW_ACTION_REVISE,
                        "reviewer_id": "user-1",
                        "feedback": "Slides repeat; diversify per the research.",
                        STRUCTURED_FEEDBACK_KEY: {
                            STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT
                        },
                    },
                )

                reopened = await engine._app.aget_state(config)
                assert reopened.next == (PHASE_CONTENT,)
                assert (
                    reopened.values["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
                )

    @pytest.mark.asyncio
    async def test_approved_carousel_holds_and_send_back_regenerates(self) -> None:
        """AE-0288: after final-review approval the graph parks at the internal
        approved_hold node (NOT END), stays publishable, and a send-back from the
        hold re-enters content so it regenerates exactly once with the publish
        lock dropped in graph state.

        get_state must hide the hold node: it reports current_phase=final_review /
        phase_status=approved (not approved_hold / awaiting_human), so the carousel
        stays publishable while held.
        """
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        from rag_backend.domain.constants.carousel_workflow import (
            CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
            PHASE_APPROVED_HOLD,
            PHASE_CONTENT,
            PHASE_STATUS_APPROVED,
            PHASE_STATUS_AWAITING_HUMAN,
            REVIEW_ACTION_REVISE,
            STRUCTURED_FEEDBACK_KEY,
            STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
        )

        class _CountingRunner:
            """Minimal artifact runner: regenerates content drafts on each run."""

            def __init__(self) -> None:
                self.content_runs = 0

            async def ensure_for_phase(
                self, state: CarouselWorkflowState
            ) -> dict[str, object]:
                if state.get("current_phase") == PHASE_CONTENT:
                    self.content_runs += 1
                    return {
                        "slide_drafts": [{"draft_text": f"gen-{self.content_runs}"}]
                    }
                return {}

        runner = _CountingRunner()
        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(
                    checkpointer=checkpointer, artifact_runner=runner
                )
                project_id = "hold-project"
                config = {"configurable": {"thread_id": project_id}}
                await engine.start(
                    project_id,
                    {"topic": "AI"},
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                # Approve research, outline, content, design, images, final_review
                # -> the graph parks at approved_hold (it does NOT reach END).
                for _ in range(6):
                    await engine.resume(
                        project_id,
                        {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                    )
                snapshot = await engine._app.aget_state(config)
                assert snapshot.next == (PHASE_APPROVED_HOLD,)

                held = await engine.get_state(project_id)
                assert held is not None
                assert held["current_phase"] == PHASE_FINAL_REVIEW
                assert held["phase_status"] == PHASE_STATUS_APPROVED
                assert (
                    held["workflow_status"] == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
                )
                assert held["quality_passed"] is True

                runs_before = runner.content_runs
                await engine.resume(
                    project_id,
                    {
                        "action": REVIEW_ACTION_REVISE,
                        "reviewer_id": "user-1",
                        "feedback": "Slides repeat; diversify per the research.",
                        STRUCTURED_FEEDBACK_KEY: {
                            STRUCTURED_FEEDBACK_TARGET_PHASE_KEY: PHASE_CONTENT
                        },
                    },
                )
                after = await engine._app.aget_state(config)
                assert after.next == (PHASE_CONTENT,)
                # Content regenerated exactly once on the send-back.
                assert runner.content_runs == runs_before + 1

                reentered = await engine.get_state(project_id)
                assert reentered is not None
                assert reentered["current_phase"] == PHASE_CONTENT
                assert reentered["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
                # The publish lock must be dropped in graph state for the whole
                # revision window (so the resume sync writes draft to the DB).
                assert (
                    reentered["workflow_status"]
                    == CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
                )
                assert reentered["quality_passed"] is False

    @pytest.mark.asyncio
    async def test_approve_resume_from_hold_finalizes_to_end(self) -> None:
        """AE-0288: an explicit approve resume of a held carousel finalizes the
        graph (END). Normal UX never does this (publishing is a separate
        endpoint), but the finalize path must be deterministic."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        from rag_backend.domain.constants.carousel_workflow import PHASE_APPROVED_HOLD

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "finalize-project"
                config = {"configurable": {"thread_id": project_id}}
                await engine.start(
                    project_id,
                    {"topic": "AI"},
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                for _ in range(6):
                    await engine.resume(
                        project_id,
                        {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                    )
                assert (
                    await engine._app.aget_state(config)
                ).next == (PHASE_APPROVED_HOLD,)

                await engine.resume(
                    project_id,
                    {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                )
                assert (await engine._app.aget_state(config)).next == ()

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

    @pytest.mark.asyncio
    async def test_update_state_without_as_node_infers_node_name(self) -> None:
        """Given a workflow paused with pending interrupt, when update_state is
        called without as_node, then the node name is inferred from the
        checkpoint snapshot's ``next`` field (AE-0025 defense-in-depth)."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "ae0025-as-node"
                await engine.start(
                    project_id,
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                # Verify we are paused at research gate
                paused = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert paused.next == (PHASE_RESEARCH,)

                # Patch the internal aupdate_state to capture as_node
                original_aupdate = engine._app.aupdate_state

                async def capturing_aupdate(
                    config: object,
                    values: object,
                    as_node: str | None = None,
                ) -> object:
                    assert as_node == PHASE_RESEARCH, (
                        f"Expected as_node='{PHASE_RESEARCH}' but got '{as_node}'"
                    )
                    return await original_aupdate(config, values, as_node=as_node)

                engine._app.aupdate_state = capturing_aupdate  # type: ignore[method-assign]

                # Call update_state WITHOUT as_node — should infer 'research'
                await engine.update_state(
                    project_id,
                    {"phase_feedback": {"research": ["looks good"]}},
                )

                # Verify the value was actually persisted
                after = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                phase_feedback = (after.values or {}).get("phase_feedback", {})
                assert isinstance(phase_feedback, dict)
                research_feedback = phase_feedback.get("research", [])
                assert "looks good" in research_feedback

    @pytest.mark.asyncio
    async def test_get_state_does_not_override_phase_status_without_interrupts(
        self,
    ) -> None:
        """Given a checkpoint with pending_next but no interrupts,
        get_state SHALL NOT override phase_status to awaiting_human."""
        from types import SimpleNamespace

        engine = CarouselWorkflowEngine()
        snapshot = SimpleNamespace(
            values={
                "current_phase": "research",
                "phase_status": "in_progress",
                "project_id": "test",
            },
            interrupts=(),
            tasks=(),
            next=("outline",),
        )
        # Monkey-patch _app.aget_state to return our test snapshot
        original_get_state = engine._app.aget_state

        async def mock_aget_state(*args: object, **kwargs: object) -> object:
            return snapshot

        engine._app.aget_state = mock_aget_state  # type: ignore[method-assign]

        state = await engine.get_state("test")

        engine._app.aget_state = original_get_state
        assert state is not None
        assert state["phase_status"] == "in_progress", (
            f"Expected 'in_progress' but got '{state.get('phase_status')}'"
        )

    @pytest.mark.asyncio
    async def test_resume_recovers_from_corrupted_checkpoint(self) -> None:
        """Given a checkpoint with pending_next, no interrupts, and
        phase_status=in_progress, resume() SHALL use Command(resume=payload)
        instead of ainvoke(None) — the corrupted-checkpoint recovery path."""
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "ae0025-corrupted"
                await engine.start(
                    project_id,
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                # Simulate the corrupted checkpoint: call update_state WITHOUT
                # as_node and with phase_status=in_progress — this clears
                # interrupts (the old bug).
                await engine._app.aupdate_state(
                    {"configurable": {"thread_id": project_id}},
                    {"phase_status": "in_progress"},
                )

                corrupted = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert corrupted.next == (PHASE_RESEARCH,)
                assert not corrupted.interrupts, (
                    "Test setup failed: interrupts should have been cleared"
                )

                with patch.object(
                    engine._app,
                    "ainvoke",
                    wraps=engine._app.ainvoke,
                ) as spy_ainvoke:
                    state = await engine.resume(
                        project_id,
                        {"action": "approve", "reviewer_id": "user-1"},
                    )

                    # Verify ainvoke was called with Command(resume=...), not None
                    call_args = spy_ainvoke.await_args
                    assert call_args is not None
                    # First positional arg is the input Command
                    command = call_args.args[0]
                    assert hasattr(command, "resume"), (
                        "Expected invoke with Command(resume=payload) "
                        f"but got: {command}"
                    )
                    assert command.resume == {
                        "action": "approve",
                        "reviewer_id": "user-1",
                    }

                    # Verify workflow actually advanced (approve consumed interrupt)
                    final_snapshot = await engine._app.aget_state({
                        "configurable": {"thread_id": project_id}
                    })
                    assert final_snapshot.next == (PHASE_OUTLINE,), (
                        f"Expected outline but got {final_snapshot.next}"
                    )

    @pytest.mark.asyncio
    async def test_reap_then_resume_re_executes_interrupted_node(self) -> None:
        """AE-0315 clean re-resume: a mid-generation reap + resume produces a
        complete, validated artifact, not a half-built one.

        Feature: tests/features/carousel_run_progress_reaper.feature
        Scenario: Dead run is reaped and the user recovers without an operator.
        The reaper NEVER rewinds or edits checkpoint state — it only flips the
        DB row. LangGraph resumes from the last node-boundary checkpoint and
        re-executes the interrupted node from its start (safe because side
        effects before ``interrupt()`` are idempotent by project rule).
        """
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
                engine = CarouselWorkflowEngine(checkpointer=checkpointer)
                project_id = "ae0315-reaped-mid-run"
                await engine.start(
                    project_id,
                    research_findings=[{"source": "report", "key_points": ["risk"]}],
                )
                # Shape the checkpoint like a run killed mid-step: pending
                # node, no live interrupt, phase_status=in_progress.
                await engine._app.aupdate_state(
                    {"configurable": {"thread_id": project_id}},
                    {"phase_status": "in_progress"},
                )
                mid_step = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                assert mid_step.next == (PHASE_RESEARCH,)
                assert not mid_step.interrupts

                # The reaper flips ONLY the carousel row (awaiting_human +
                # lock/epoch bump) — the checkpoint above stays untouched.
                # The user's next resume re-executes the interrupted node.
                state = await engine.resume(
                    project_id,
                    {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"},
                )

                assert state["research_approved"] is True
                final_snapshot = await engine._app.aget_state({
                    "configurable": {"thread_id": project_id}
                })
                # A complete node re-execution: the workflow advanced past the
                # reaped node to the next gate (no half-built stall).
                assert final_snapshot.next == (PHASE_OUTLINE,)
