"""A failed phase must leave the graph, and a retry must be able to re-enter it.

Scenarios: see tests/features/carousel_failed_phase_terminates.feature

Live 2026-09-14 (AE-0330): the content node returned early on
``phase_status=failed`` without interrupting, and the gate routed it straight
back into itself — ~10,000 steps at 4/s with no LLM call, until langgraph's
10007 recursion limit. It happened twice on one project: first on a genuine
draft failure, then again with all drafts present because resume never clears
the stale ``failed`` flag from the checkpoint.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.carousel_workflow_graph import (
    build_carousel_workflow_graph,
    needs_gate_reopen,
    route_after_design,
    route_after_gate,
)
from rag_backend.agents.carousel_workflow_nodes import content_phase_async
from rag_backend.application.services.carousel.workflow_state import (
    get_initial_carousel_state,
)
from rag_backend.domain.constants.ai_agents import ERR_INVALID_JSON
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_GRAPH_RECURSION_LIMIT,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    WORKFLOW_ERROR_KEY,
)

ROUTE_FAILED = "failed"
_DRAFTS: list[dict[str, object]] = [{"slide_index": 1, "draft_text": "copy"}]


def _state(**overrides: object) -> dict[str, object]:
    state = get_initial_carousel_state("project-1", {"topic": "AI"})
    state.update(overrides)
    return state


class _Runner:
    """Artifact-runner stand-in: fails or succeeds the content phase on demand."""

    def __init__(self, *, fail_content: bool) -> None:
        self.fail_content = fail_content
        self.calls: list[str] = []

    async def ensure_for_phase(self, state: dict[str, object]) -> dict[str, object]:
        phase = str(state.get("current_phase", ""))
        self.calls.append(phase)
        if phase != PHASE_CONTENT:
            return {}
        if self.fail_content:
            return {
                "phase_status": PHASE_STATUS_FAILED,
                WORKFLOW_ERROR_KEY: ERR_INVALID_JSON,
            }
        return {"slide_drafts": list(_DRAFTS)}


class TestFailedRouting:
    def test_failed_phase_routes_out_of_the_gate(self) -> None:
        # Scenario: a failed phase leaves the graph instead of retrying itself
        state = _state(phase_status=PHASE_STATUS_FAILED, content_approved=False)
        assert route_after_gate(state, "content_approved") == ROUTE_FAILED

    def test_failed_wins_even_when_the_approved_flag_is_set(self) -> None:
        state = _state(phase_status=PHASE_STATUS_FAILED, content_approved=True)
        assert route_after_gate(state, "content_approved") == ROUTE_FAILED

    def test_design_gate_also_routes_failed_out(self) -> None:
        state = _state(phase_status=PHASE_STATUS_FAILED)
        assert route_after_design(state) == ROUTE_FAILED

    def test_healthy_routing_is_unchanged(self) -> None:
        assert route_after_gate(_state(content_approved=True), "content_approved") == (
            "approved"
        )
        assert route_after_gate(_state(content_approved=False), "content_approved") == (
            "retry"
        )

    def test_every_gated_phase_maps_failed_to_end(self) -> None:
        # Scenario: the graph wires the failed route to END on every gate
        graph = build_carousel_workflow_graph()
        for phase in (PHASE_RESEARCH, PHASE_OUTLINE, PHASE_CONTENT, PHASE_DESIGN):
            branches = graph.branches[phase].values()
            assert any(b.ends and b.ends.get(ROUTE_FAILED) == END for b in branches), (
                phase
            )


class TestFailedGateReopen:
    @staticmethod
    def _snapshot(**values: object) -> SimpleNamespace:
        base: dict[str, object] = {"current_phase": PHASE_CONTENT}
        base.update(values)
        return SimpleNamespace(next=(), values=base)

    def test_failed_phase_at_end_is_reopened_on_retry(self) -> None:
        # Scenario: a retry re-enters a failed phase parked at END
        snap = self._snapshot(phase_status=PHASE_STATUS_FAILED, content_approved=False)
        assert needs_gate_reopen(snap) is True

    def test_awaiting_human_reopen_still_works(self) -> None:
        snap = self._snapshot(
            phase_status=PHASE_STATUS_AWAITING_HUMAN, content_approved=False
        )
        assert needs_gate_reopen(snap) is True

    def test_other_statuses_do_not_reopen(self) -> None:
        snap = self._snapshot(phase_status=PHASE_STATUS_IN_PROGRESS)
        assert needs_gate_reopen(snap) is False


class TestContentNodeFailedHandling:
    @staticmethod
    def _config(runner: _Runner) -> dict[str, object]:
        return {"configurable": {"artifact_runner": runner}}

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    async def test_fresh_failure_returns_without_interrupting(
        self, mock_interrupt: object
    ) -> None:
        # Scenario: a fresh artifact failure does not open a review gate
        runner = _Runner(fail_content=True)

        result = await content_phase_async(
            _state(phase_status=PHASE_STATUS_IN_PROGRESS), self._config(runner)
        )

        assert result["phase_status"] == PHASE_STATUS_FAILED
        assert result[WORKFLOW_ERROR_KEY] == ERR_INVALID_JSON
        assert result["current_phase"] == PHASE_CONTENT  # names the failed phase
        mock_interrupt.assert_not_called()  # type: ignore[attr-defined]

    @patch("rag_backend.agents.carousel_workflow_nodes.interrupt")
    async def test_stale_failure_is_cleared_when_artifacts_succeed(
        self, mock_interrupt: object
    ) -> None:
        # Scenario: a stale failed flag does not block a successful rebuild
        mock_interrupt.return_value = {"action": REVIEW_ACTION_APPROVE}  # type: ignore[attr-defined]
        runner = _Runner(fail_content=False)
        stale = _state(
            phase_status=PHASE_STATUS_FAILED,
            **{WORKFLOW_ERROR_KEY: ERR_INVALID_JSON},
        )

        result = await content_phase_async(stale, self._config(runner))

        mock_interrupt.assert_called_once()  # type: ignore[attr-defined]
        assert result["slide_drafts"] == _DRAFTS
        assert result["phase_status"] != PHASE_STATUS_FAILED
        assert result[WORKFLOW_ERROR_KEY] == ""
        assert result["content_approved"] is True


class TestEngineTerminatesInsteadOfLooping:
    def test_run_config_bounds_recursion(self) -> None:
        # Scenario: the graph runs under an explicit recursion limit
        config = CarouselWorkflowEngine()._run_config("p")
        assert config["recursion_limit"] == CAROUSEL_GRAPH_RECURSION_LIMIT
        assert CAROUSEL_GRAPH_RECURSION_LIMIT < 10007

    async def test_failed_content_ends_the_run_and_a_retry_reenters(self) -> None:
        # Scenario: a content failure ends the run; the retry rebuilds and proceeds.
        # Without the fix this raises GraphRecursionError — the live loop.
        runner = _Runner(fail_content=True)
        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
                engine = CarouselWorkflowEngine(
                    checkpointer=saver, artifact_runner=runner
                )
                project_id = "failed-content"
                cfg = {"configurable": {"thread_id": project_id}}
                approve = {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "u"}

                await engine.start(
                    project_id,
                    {"topic": "AI"},
                    research_findings=[{"source": "s", "key_points": ["k"]}],
                )
                await engine.resume(project_id, approve)  # research -> outline gate
                state = await engine.resume(project_id, approve)  # outline -> content

                assert state["phase_status"] == PHASE_STATUS_FAILED
                assert state[WORKFLOW_ERROR_KEY] == ERR_INVALID_JSON
                assert state["current_phase"] == PHASE_CONTENT
                ended = await engine._app.aget_state(cfg)
                assert ended.next == ()  # left the graph, did not loop
                assert runner.calls.count(PHASE_CONTENT) == 1

                runner.fail_content = False
                state = await engine.resume(project_id, approve)  # the retry

                assert state["slide_drafts"] == _DRAFTS
                assert state["phase_status"] != PHASE_STATUS_FAILED
                assert state["content_approved"] is True
                after = await engine._app.aget_state(cfg)
                assert after.next == (PHASE_DESIGN,)
                assert runner.calls.count(PHASE_CONTENT) == 2


@pytest.mark.parametrize("phase", [PHASE_RESEARCH, PHASE_OUTLINE, PHASE_CONTENT])
def test_failed_route_name_is_stable(phase: str) -> None:
    field = {
        PHASE_RESEARCH: "research_approved",
        PHASE_OUTLINE: "outline_approved",
    }.get(phase, "content_approved")
    assert route_after_gate(_state(phase_status=PHASE_STATUS_FAILED), field) == "failed"
