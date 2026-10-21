"""Re-drive a parked workflow node: service, runner, engine.

Gherkin: tests/features/autopilot_runner.feature
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from rag_backend.agents.carousel_editorial_orchestrator import (
    CarouselEditorialOrchestrator,
)
from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel import (
    editorial_workflow_resume_runner as resume_runner,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_NOTHING_TO_REDRIVE,
    PHASE_CONTENT,
    REVIEW_ACTION_APPROVE,
    RUN_ACTION_REDRIVE,
)

_PROJECT = "22222222-2222-2222-2222-222222222222"
_SERVICE = "rag_backend.application.services.carousel.editorial_workflow_service"
_RETURNED = {"current_phase": PHASE_CONTENT, "phase_status": "in_progress"}
_PERSISTED = {"current_phase": PHASE_CONTENT, "phase_status": "awaiting_human"}


def _service(
    persisted: dict[str, object] | None,
) -> tuple[EditorialWorkflowService, MagicMock]:
    service = EditorialWorkflowService(EditorialWorkflowConfig(llm=MagicMock()))
    orchestrator = MagicMock()
    orchestrator.continue_pending = AsyncMock(return_value=dict(_RETURNED))
    orchestrator.get_state = AsyncMock(return_value=persisted)
    orchestrator.engine.is_parked = AsyncMock(return_value=True)
    service._orchestrator = orchestrator
    return service, orchestrator


@pytest.mark.asyncio
async def test_redrive_runs_the_pending_node_and_syncs_the_row() -> None:
    """Scenario: A re-drive runs the node with an empty resume context.

    The sync is committed at once so the row lock is released.
    """
    service, orchestrator = _service(dict(_PERSISTED))
    db = MagicMock()
    with (
        patch(f"{_SERVICE}.CarouselProjectWriteOwner") as owner,
        patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()) as sse,
    ):
        owner.return_value.sync_phase = AsyncMock()
        owner.return_value.commit = AsyncMock()
        state = await service.redrive_pending_phase(_PROJECT, db)

    assert state == _PERSISTED
    orchestrator.continue_pending.assert_awaited_once_with(
        _PROJECT,
        db=db,
        workflow_input=EditorialWorkflowStartInput(
            topic="", audience="", brief="", sources=[], user_id=""
        ),
    )
    owner.assert_called_with(db)
    owner.return_value.sync_phase.assert_awaited_once_with(_PROJECT, _PERSISTED)
    owner.return_value.commit.assert_awaited_once_with()
    sse.assert_awaited_once_with(_PROJECT, _PERSISTED)


@pytest.mark.asyncio
async def test_redrive_falls_back_to_the_returned_state() -> None:
    service, _orchestrator = _service(None)
    with patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()) as sse:
        state = await service.redrive_pending_phase(_PROJECT, None)
    assert state == _RETURNED
    sse.assert_awaited_once_with(_PROJECT, _RETURNED)


@pytest.mark.asyncio
async def test_is_parked_delegates_to_the_engine() -> None:
    service, orchestrator = _service(None)
    assert await service.is_parked_before_node(_PROJECT) is True
    orchestrator.engine.is_parked.assert_awaited_once_with(_PROJECT)


def _params(action: str) -> resume_runner.BackgroundResumeParams:
    return resume_runner.BackgroundResumeParams(
        project_id=_PROJECT,
        action=action,
        reviewer_id="reviewer",
        feedback="fb",
        project_title="title",
        structured_feedback={"target_phase": PHASE_CONTENT},
    )


@pytest.mark.asyncio
async def test_run_phase_redrive_never_sends_a_review() -> None:
    """Scenario: The run wrapper re-drives instead of resuming.

    The re-drive loads the project's persona, like a resume.
    """
    service = MagicMock()
    service.redrive_pending_phase = AsyncMock(return_value=dict(_PERSISTED))
    service.resume_workflow = AsyncMock()
    db = MagicMock()
    persona = MagicMock(name="persona")
    with patch(
        "rag_backend.application.services.carousel.resume_persona.load_project_persona",
        new_callable=AsyncMock,
        return_value=persona,
    ) as load:
        state = await resume_runner._run_phase(service, _params(RUN_ACTION_REDRIVE), db)
    assert state == _PERSISTED
    load.assert_awaited_once_with(db, _PROJECT)
    service.redrive_pending_phase.assert_awaited_once_with(_PROJECT, db, persona)
    service.resume_workflow.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_phase_review_passes_every_field() -> None:
    """The resume loads the project's persona (none here)."""
    service = MagicMock()
    service.resume_workflow = AsyncMock(return_value=dict(_PERSISTED))
    service.redrive_pending_phase = AsyncMock()
    db = MagicMock()
    with patch(
        "rag_backend.application.services.carousel.resume_persona.load_project_persona",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await resume_runner._run_phase(service, _params(REVIEW_ACTION_APPROVE), db)
    service.redrive_pending_phase.assert_not_awaited()
    service.resume_workflow.assert_awaited_once_with(
        ResumeWorkflowInput(
            project_id=_PROJECT,
            action=REVIEW_ACTION_APPROVE,
            reviewer_id="reviewer",
            feedback="fb",
            db=db,
            persona=None,
            project_title="title",
            structured_feedback={"target_phase": PHASE_CONTENT},
        )
    )


@dataclass(frozen=True)
class _Snapshot:
    next: tuple[str, ...] = ()
    interrupts: tuple[object, ...] = ()
    tasks: tuple[object, ...] = ()


def _engine(snapshot: _Snapshot) -> tuple[CarouselWorkflowEngine, MagicMock]:
    engine = CarouselWorkflowEngine(checkpointer=MemorySaver())
    app = MagicMock()
    app.aget_state = AsyncMock(return_value=snapshot)
    app.ainvoke = AsyncMock(return_value=dict(_PERSISTED))
    engine._app = app
    return engine, app


@pytest.mark.asyncio
async def test_engine_continue_pending_invokes_with_no_resume_value() -> None:
    """Scenario: A re-drive never feeds a null resume to the next gate."""
    engine, app = _engine(_Snapshot(next=(PHASE_CONTENT,)))
    assert await engine.is_parked(_PROJECT) is True
    state = await engine.continue_pending(_PROJECT)
    assert state == _PERSISTED
    args, kwargs = app.ainvoke.await_args
    assert args == (None,)
    assert kwargs["config"]["configurable"]["thread_id"] == _PROJECT


@pytest.mark.asyncio
async def test_engine_continue_pending_refuses_an_open_gate() -> None:
    engine, app = _engine(_Snapshot(next=(PHASE_CONTENT,), interrupts=("gate",)))
    assert await engine.is_parked(_PROJECT) is False
    with pytest.raises(ValueError, match=ERR_NOTHING_TO_REDRIVE):
        await engine.continue_pending(_PROJECT)
    app.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_binds_the_context_before_continuing() -> None:
    orchestrator = CarouselEditorialOrchestrator(llm=MagicMock())
    engine = MagicMock()
    engine.continue_pending = AsyncMock(return_value=dict(_PERSISTED))
    orchestrator._engine = engine
    db = MagicMock()
    workflow_input = EditorialWorkflowStartInput(
        topic="", audience="", brief="", sources=[]
    )
    state = await orchestrator.continue_pending(
        _PROJECT, db=db, workflow_input=workflow_input
    )
    assert state == _PERSISTED
    engine.continue_pending.assert_awaited_once_with(_PROJECT)
    runner = engine.set_artifact_runner.call_args.args[0]
    assert runner._db is db
    assert runner._workflow_input is workflow_input


@pytest.mark.asyncio
async def test_redrive_runs_the_node_with_the_project_persona() -> None:
    """Scenario: a re-drive drafts and scores with the persona."""
    service, orchestrator = _service(dict(_PERSISTED))
    persona = MagicMock(name="persona")
    with (
        patch(f"{_SERVICE}.CarouselProjectWriteOwner") as owner,
        patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()),
    ):
        owner.return_value.sync_phase = AsyncMock()
        owner.return_value.commit = AsyncMock()
        await service.redrive_pending_phase(_PROJECT, MagicMock(), persona)
    workflow_input = orchestrator.continue_pending.await_args.kwargs["workflow_input"]
    assert workflow_input.persona is persona
