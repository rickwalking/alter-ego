"""AE-0314 feasibility proof: editing a parked approved-hold thread.

The post-completion slide-edit endpoint writes the edited copy + a fresh
validation report to the checkpoint via the engine ``update_state`` wrapper
(source-of-truth option (a), pinned in the ticket Decision Log). Approved
carousels do NOT reach END — the graph parks at the internal
``approved_hold`` interrupt precisely so they stay resumable (AE-0288).

This proof MUST pass before any feature code: it drives a real workflow to the
approved-hold park via an ``AsyncSqliteSaver`` checkpointer, calls the engine's
``update_state`` wrapper WITHOUT ``as_node`` (the production call shape), and
asserts:

  (i)  the write lands — the patched value is visible on the reloaded state;
  (ii) the pending interrupt is preserved — the thread is still parked at
       ``approved_hold`` (the documented ``as_node`` clearing footgun in
       ``carousel_workflow_engine.py`` is asserted against, not merely trusted).

Feature file: tests/features/carousel_text_edit_no_regen.feature
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_APPROVED,
    REVIEW_ACTION_APPROVE,
)

_EDITED_HEADING = "Corrected Heading"


async def _drive_to_approved_hold(
    engine: CarouselWorkflowEngine, project_id: str
) -> None:
    """Approve all six review gates so the graph parks at approved_hold."""
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


@pytest.mark.asyncio
async def test_update_state_on_approved_hold_lands_and_preserves_interrupt() -> None:
    """AE-0314 #1: aupdate_state on a parked approved-hold thread is safe.

    Scenario: Fix a typo on a completed carousel (checkpoint convergence path).
    """
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "workflow.sqlite"
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            engine = CarouselWorkflowEngine(checkpointer=checkpointer)
            project_id = "ae0314-hold-edit"
            config = {"configurable": {"thread_id": project_id}}
            await _drive_to_approved_hold(engine, project_id)

            parked = await engine._app.aget_state(config)
            assert parked.next == (PHASE_APPROVED_HOLD,)

            # Production call: patch_parked_checkpoint writes with as_node=None so
            # the park is preserved.
            fresh_report: dict[str, object] = {"blocking": False, "violations": []}
            values: dict[str, object] = {
                WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [
                    {"slide_index": 1, "presentation_pt": {"heading": _EDITED_HEADING}}
                ],
                WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: fresh_report,
            }
            patched = await engine.patch_parked_checkpoint(project_id, values)
            assert patched is True

            # (i) the write lands.
            after = await engine._app.aget_state(config)
            slides = after.values[WORKFLOW_STATE_LOCALIZED_SLIDES_KEY]
            assert slides[0]["presentation_pt"]["heading"] == _EDITED_HEADING
            assert (
                after.values[WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY] == fresh_report
            )

            # (ii) the pending interrupt is preserved — still parked at the hold.
            assert after.next == (PHASE_APPROVED_HOLD,)

            # get_state keeps the carousel publishable (the hold stays hidden).
            held = await engine.get_state(project_id)
            assert held is not None
            assert held["current_phase"] == PHASE_FINAL_REVIEW
            assert held["phase_status"] == PHASE_STATUS_APPROVED


@pytest.mark.asyncio
async def test_inferred_as_node_footgun_advances_hold_to_end() -> None:
    """AE-0314 #1: the naive inferred-as_node path is the footgun being avoided.

    Explicitly assert AGAINST the footgun: ``update_state`` (as_node inferred as
    ``approved_hold``) treats the hold node as complete and advances it to END
    (``next == ()``), losing the park. This is why the edit path uses
    ``patch_parked_checkpoint`` (as_node=None) instead.
    """
    with TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "workflow.sqlite"
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            engine = CarouselWorkflowEngine(checkpointer=checkpointer)
            project_id = "ae0314-footgun"
            config = {"configurable": {"thread_id": project_id}}
            await _drive_to_approved_hold(engine, project_id)
            assert (await engine._app.aget_state(config)).next == (PHASE_APPROVED_HOLD,)

            await engine.update_state(
                project_id,
                {WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: []},
            )
            # The footgun: the hold was advanced to END, park lost.
            assert (await engine._app.aget_state(config)).next == ()
