"""The graph sends an approved carousel back to the final-review interrupt.

Gherkin: tests/features/reopen_review_on_cover_switch_ae0597.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.agents.carousel_review_reopen import (
    reopen_review_updates,
    reopens_final_review,
)
from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.agents.carousel_workflow_graph import route_after_hold
from rag_backend.agents.carousel_workflow_nodes import review_updates_from_response
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    PHASE_APPROVED_HOLD,
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REOPEN,
    SEND_BACK_TARGET_PHASE_KEY,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)

_APPROVE = {"action": REVIEW_ACTION_APPROVE, "reviewer_id": "user-1"}


@asynccontextmanager
async def _held(project_id: str) -> AsyncIterator[CarouselWorkflowEngine]:
    """An engine whose thread is approved and parked at the approved hold."""
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "workflow.sqlite"
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            engine = CarouselWorkflowEngine(checkpointer=checkpointer)
            await engine.start(
                project_id,
                {"topic": "AI"},
                research_findings=[{"source": "report", "key_points": ["risk"]}],
            )
            for _ in range(6):
                await engine.resume(project_id, _APPROVE)
            yield engine


async def _next(engine: CarouselWorkflowEngine, project_id: str) -> tuple[str, ...]:
    snapshot = await engine._app.aget_state({"configurable": {"thread_id": project_id}})
    return tuple(snapshot.next)


@pytest.mark.unit
class TestReopenUpdates:
    # Scenario: A cover switch reopens the review of an approved carousel
    def test_a_reopen_resume_drops_the_approval(self) -> None:
        updates = review_updates_from_response({"action": REVIEW_ACTION_REOPEN})

        assert updates == reopen_review_updates()
        assert updates["workflow_status"] == CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
        assert updates["quality_passed"] is False
        assert updates["phase_status"] == PHASE_STATUS_AWAITING_HUMAN

    # Scenario: A cover switch reopens the review of an approved carousel
    def test_the_hold_routes_a_reopen_to_the_final_review(self) -> None:
        state: CarouselWorkflowState = {
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            SEND_BACK_TARGET_PHASE_KEY: PHASE_FINAL_REVIEW,
        }

        assert reopens_final_review(state)
        assert route_after_hold(state) == PHASE_FINAL_REVIEW

    # Scenario: A cover switch reopens the review of an approved carousel
    def test_other_hold_resumes_keep_their_routes(self) -> None:
        approved: CarouselWorkflowState = {
            "phase_status": PHASE_STATUS_APPROVED,
            SEND_BACK_TARGET_PHASE_KEY: PHASE_FINAL_REVIEW,
        }
        send_back: CarouselWorkflowState = {
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
            SEND_BACK_TARGET_PHASE_KEY: PHASE_CONTENT,
        }

        assert not reopens_final_review(approved)
        assert route_after_hold(approved) == "done"
        assert route_after_hold(send_back) == PHASE_CONTENT


@pytest.mark.unit
class TestEngineReopen:
    # Scenario: A cover switch reopens the review of an approved carousel
    # Scenario: A fresh approve restores the approval
    @pytest.mark.asyncio
    async def test_a_held_carousel_waits_at_the_final_review_again(self) -> None:
        project_id = "reopen-project"
        async with _held(project_id) as engine:
            assert await _next(engine, project_id) == (PHASE_APPROVED_HOLD,)

            assert await engine.reopen_final_review(project_id) is True

            assert await _next(engine, project_id) == (PHASE_FINAL_REVIEW,)
            reopened = await engine.get_state(project_id)
            assert reopened is not None
            assert reopened["current_phase"] == PHASE_FINAL_REVIEW
            assert reopened["phase_status"] == PHASE_STATUS_AWAITING_HUMAN
            assert reopened["workflow_status"] == (
                CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
            )
            assert reopened["quality_passed"] is False

            await engine.resume(project_id, _APPROVE)

            assert await _next(engine, project_id) == (PHASE_APPROVED_HOLD,)
            approved = await engine.get_state(project_id)
            assert approved is not None
            assert approved["workflow_status"] == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            assert approved["phase_status"] == PHASE_STATUS_APPROVED
            assert approved["quality_passed"] is True

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_a_thread_already_in_review_counts_as_reopened(self) -> None:
        """An earlier reopen whose row write never committed is not redone."""
        project_id = "reopen-twice"
        async with _held(project_id) as engine:
            assert await engine.reopen_final_review(project_id) is True

            assert await engine.reopen_final_review(project_id) is True
            assert await _next(engine, project_id) == (PHASE_FINAL_REVIEW,)

    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    @pytest.mark.asyncio
    async def test_a_finished_thread_cannot_be_reopened(self) -> None:
        project_id = "reopen-finished"
        async with _held(project_id) as engine:
            await engine.resume(project_id, _APPROVE)
            assert await _next(engine, project_id) == ()

            assert await engine.reopen_final_review(project_id) is False

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_without_a_checkpointer_nothing_is_reopened(self) -> None:
        engine = CarouselWorkflowEngine(checkpointer=None)

        assert await engine.reopen_final_review("no-thread") is False

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_an_unknown_thread_is_left_alone(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "workflow.sqlite"
            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
                engine = CarouselWorkflowEngine(checkpointer=saver)

                assert await engine.reopen_final_review("unknown") is False
