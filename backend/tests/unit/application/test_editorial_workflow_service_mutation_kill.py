"""Exact-behaviour tests for EditorialWorkflowService start/resume/redrive.

Feature: Carousel editorial workflow safety net (start, resume, re-drive)
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
    ResumeWorkflowInput,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    STRUCTURED_FEEDBACK_KEY,
)

_SERVICE = "rag_backend.application.services.carousel.editorial_workflow_service"
_SUPPORT = "rag_backend.application.services.carousel.editorial_workflow_support"
_PROJECT_ID = "proj-42"
_REVIEWER_ID = "reviewer-9"
_USER_ID = "user-1"
_TOPIC = "topic"

StateMap = dict[str, dict[str, object]]


def _keyed_get_state(states: StateMap) -> AsyncMock:
    """Return a get_state double that answers only for the right project id."""

    async def get_state(project_id: str) -> dict[str, object] | None:
        return states.get(project_id)

    return AsyncMock(side_effect=get_state)


@pytest.fixture
def events() -> MagicMock:
    return MagicMock()


@pytest.fixture
def notifications() -> MagicMock:
    notification_service = MagicMock()
    notification_service.create_review_request = AsyncMock()
    return notification_service


@pytest.fixture
def service(events: MagicMock, notifications: MagicMock) -> EditorialWorkflowService:
    built = EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=MagicMock(),
            event_service=events,
            notification_service=notifications,
        )
    )
    built._orchestrator = MagicMock()
    return built


@pytest.fixture
def write_owner() -> Iterator[MagicMock]:
    with (
        patch(f"{_SERVICE}.CarouselProjectWriteOwner") as owner,
        patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()),
    ):
        owner.return_value.assign_reviewer = AsyncMock()
        owner.return_value.sync_phase = AsyncMock()
        owner.return_value.commit = AsyncMock()
        yield owner


def _db() -> AsyncMock:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    return db


@pytest.mark.unit
class TestStartWorkflowExact:
    """Scenario: Workflow start seeds the brief and assigns the reviewer."""

    async def test_existing_state_for_project_is_returned(
        self, service: EditorialWorkflowService
    ) -> None:
        existing: dict[str, object] = {"current_phase": PHASE_RESEARCH}
        service._orchestrator.get_state = _keyed_get_state({_PROJECT_ID: existing})
        service._orchestrator.start = AsyncMock()
        state = await service.start_workflow(
            _PROJECT_ID, MagicMock(user_id=_USER_ID, reviewer_id=None)
        )
        assert state is existing
        service._orchestrator.start.assert_not_awaited()

    async def test_brief_reviewer_and_review_request_are_exact(
        self,
        service: EditorialWorkflowService,
        notifications: MagicMock,
        write_owner: MagicMock,
    ) -> None:
        orchestrator = service._orchestrator
        orchestrator.get_state = AsyncMock(return_value=None)
        orchestrator.enrich_research_sources = AsyncMock(return_value=[])
        orchestrator.synthesize_research = AsyncMock(return_value=[])
        orchestrator.start = AsyncMock(return_value={"current_phase": PHASE_RESEARCH})
        orchestrator.update_state = AsyncMock()
        db = _db()
        with patch(f"{_SERVICE}.emit_phase_event", new=AsyncMock()):
            await service.start_workflow(
                _PROJECT_ID,
                EditorialWorkflowStartInput(
                    topic=_TOPIC,
                    audience="aud",
                    brief="the brief",
                    sources=[],
                    user_id=_USER_ID,
                    reviewer_id=_REVIEWER_ID,
                ),
                db,
            )
        assert orchestrator.start.await_args.args[1] == {
            "topic": _TOPIC,
            "audience": "aud",
            "brief": "the brief",
            "sources": [],
        }
        orchestrator.update_state.assert_awaited_once_with(
            _PROJECT_ID, {"assigned_reviewer_id": _REVIEWER_ID}
        )
        write_owner.return_value.assign_reviewer.assert_awaited_once_with(
            _PROJECT_ID, _REVIEWER_ID
        )
        assert notifications.create_review_request.await_args.kwargs["user_id"] == (
            _REVIEWER_ID
        )


@pytest.mark.unit
class TestResumeWorkflowExact:
    """Scenario: Workflow resume forwards the decision and persisted state."""

    async def test_resume_forwards_db_feedback_and_persisted_state(
        self,
        service: EditorialWorkflowService,
        events: MagicMock,
        write_owner: MagicMock,
    ) -> None:
        prior: dict[str, object] = {"current_phase": PHASE_CONTENT}
        persisted: dict[str, object] = {
            "current_phase": "design",
            "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        }
        states: StateMap = {_PROJECT_ID: prior}
        orchestrator = service._orchestrator
        orchestrator.get_state = _keyed_get_state(states)

        async def resume(*_args: object, **_kwargs: object) -> dict[str, object]:
            states[_PROJECT_ID] = persisted
            return {"current_phase": "stale"}

        orchestrator.resume = AsyncMock(side_effect=resume)
        structured: dict[str, object] = {"slides": []}
        db = _db()
        with (
            patch(f"{_SERVICE}.prepare_resume_workflow", new=AsyncMock()),
            patch(f"{_SERVICE}.record_human_review"),
            patch(f"{_SERVICE}.persist_edited_slide_copy", new=AsyncMock()),
            patch(f"{_SERVICE}.emit_review_event", new=AsyncMock()) as emit,
        ):
            state = await service.resume_workflow(
                ResumeWorkflowInput(
                    project_id=_PROJECT_ID,
                    action=REVIEW_ACTION_APPROVE,
                    reviewer_id=_REVIEWER_ID,
                    db=db,
                    structured_feedback=structured,
                )
            )
        assert state is persisted
        resume_call = orchestrator.resume.await_args
        assert resume_call.args[1][STRUCTURED_FEEDBACK_KEY] == structured
        assert resume_call.kwargs["db"] is db
        request = emit.await_args.args[0]
        assert request.event_service is events
        assert request.context.prior is prior


@pytest.mark.unit
class TestRedriveAndErrorEventExact:
    """Scenario: re-drive and error events read the project's own checkpoint."""

    async def test_redrive_returns_persisted_state(
        self, service: EditorialWorkflowService, write_owner: MagicMock
    ) -> None:
        persisted: dict[str, object] = {"current_phase": "design"}
        service._orchestrator.continue_pending = AsyncMock(
            return_value={"current_phase": "stale"}
        )
        service._orchestrator.get_state = _keyed_get_state({_PROJECT_ID: persisted})
        assert await service.redrive_pending_phase(_PROJECT_ID, None) is persisted

    async def test_error_event_uses_project_phase(
        self, service: EditorialWorkflowService
    ) -> None:
        service._orchestrator.get_state = _keyed_get_state({
            _PROJECT_ID: {"current_phase": PHASE_RESEARCH}
        })
        with patch(f"{_SUPPORT}.publish_workflow_error", new=AsyncMock()) as publish:
            await service.publish_resume_error_event(
                _PROJECT_ID, message="boom", recoverable=True
            )
        assert publish.await_args.args[0].phase == PHASE_RESEARCH


@pytest.mark.unit
class TestStartWorkflowEventsAndSse:
    """Scenario: Workflow start emits the phase event for the user and publishes SSE."""

    async def test_phase_event_carries_user_and_sse_targets_project(
        self, service: EditorialWorkflowService
    ) -> None:
        started: dict[str, object] = {"current_phase": PHASE_RESEARCH}
        orchestrator = service._orchestrator
        orchestrator.get_state = AsyncMock(return_value=None)
        orchestrator.enrich_research_sources = AsyncMock(return_value=[])
        orchestrator.synthesize_research = AsyncMock(return_value=[])
        orchestrator.start = AsyncMock(return_value=started)
        with (
            patch(f"{_SERVICE}.emit_phase_event", new=AsyncMock()) as emit,
            patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()) as sse,
        ):
            await service.start_workflow(
                _PROJECT_ID,
                EditorialWorkflowStartInput(
                    topic=_TOPIC,
                    audience="aud",
                    brief="the brief",
                    sources=[],
                    user_id=_USER_ID,
                ),
            )
        ctx = emit.await_args.kwargs["ctx"]
        assert ctx.project_id == _PROJECT_ID
        assert ctx.user_id == _USER_ID
        sse.assert_awaited_once_with(_PROJECT_ID, started)

