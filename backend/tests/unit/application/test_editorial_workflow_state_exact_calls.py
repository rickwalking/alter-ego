"""Exact behaviour of EditorialWorkflowService state reads and run marking.

Feature: Carousel editorial workflow safety net (state, in-progress marking, start)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.workflow_validation import CONTENT_TYPE_CAROUSEL
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

_SERVICE = "rag_backend.application.services.carousel.editorial_workflow_service"
_SUPPORT = "rag_backend.application.services.carousel.editorial_workflow_support"
_PROJECT_ID = "proj-state-1"
_USER_ID = "user-3"
_REVIEWER_ID = "reviewer-5"
_TOPIC = "Agent guardrails"
_POLICY_VERSION = "v2"
_CURRENT_PHASE_KEY = "current_phase"
_PHASE_STATUS_KEY = "phase_status"
_PROJECT_ID_KEY = "project_id"
_EXTRA_KEY = "revision_count"
_POLICY_KEY = "presentation_policy_version"
_PROGRESS = {"slides_done": 2}
_PUBLISH_RUN_STARTED = "_publish_run_started"
_SYNC_PROJECT_PHASE = "_sync_project_phase"
_GET_WORKFLOW_STATE = "get_workflow_state"


def _keyed_get_state(states: dict[str, dict[str, object]]) -> AsyncMock:
    """Return a get_state double that answers only for the right project id."""

    async def get_state(project_id: str) -> dict[str, object] | None:
        return states.get(project_id)

    return AsyncMock(side_effect=get_state)


@pytest.fixture
def notifications() -> MagicMock:
    service = MagicMock()
    service.create_review_request = AsyncMock()
    return service


@pytest.fixture
def orchestrator() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(
    notifications: MagicMock, orchestrator: MagicMock
) -> EditorialWorkflowService:
    built = EditorialWorkflowService(
        EditorialWorkflowConfig(llm=MagicMock(), notification_service=notifications)
    )
    built._orchestrator = orchestrator
    return built


def _project(phase_status: str) -> MagicMock:
    project = MagicMock()
    project.phase_status = phase_status
    return project


@pytest.mark.unit
class TestGetWorkflowState:
    """Scenario: a checkpoint without a phase is no workflow; DB in_progress wins."""

    async def test_checkpoint_without_a_phase_is_no_workflow(
        self, service: EditorialWorkflowService, orchestrator: MagicMock
    ) -> None:
        orchestrator.get_state = AsyncMock(
            return_value={_PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN}
        )
        assert await service.get_workflow_state(_PROJECT_ID) is None

    async def test_db_in_progress_overrides_awaiting_human(
        self, service: EditorialWorkflowService, orchestrator: MagicMock
    ) -> None:
        orchestrator.get_state = AsyncMock(
            return_value={
                _CURRENT_PHASE_KEY: PHASE_RESEARCH,
                _PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN,
            }
        )
        db = AsyncMock()
        db.get = AsyncMock(return_value=_project(PHASE_STATUS_IN_PROGRESS))
        state = await service.get_workflow_state(_PROJECT_ID, db)
        assert state is not None
        assert dict(state)[_PHASE_STATUS_KEY] == PHASE_STATUS_IN_PROGRESS
        db.get.assert_awaited_once_with(CarouselProjectModel, _PROJECT_ID)


@pytest.fixture
def marking(service: EditorialWorkflowService) -> Iterator[tuple[AsyncMock, ...]]:
    with (
        patch.object(service, _SYNC_PROJECT_PHASE, new=AsyncMock()) as sync,
        patch.object(service, _PUBLISH_RUN_STARTED, new=AsyncMock()) as run_started,
        patch(
            f"{_SUPPORT}.publish_workflow_phase_change", new=AsyncMock()
        ) as phase_change,
    ):
        yield sync, run_started, phase_change


@pytest.mark.unit
class TestMarkResumeInProgress:
    """Scenario: marking a resume flips the row and broadcasts the project's phase."""

    async def test_marking_syncs_broadcasts_and_starts_the_run_exactly(
        self,
        service: EditorialWorkflowService,
        orchestrator: MagicMock,
        marking: tuple[AsyncMock, ...],
    ) -> None:
        sync, run_started, phase_change = marking
        orchestrator.get_state = _keyed_get_state({
            _PROJECT_ID: {
                _CURRENT_PHASE_KEY: PHASE_RESEARCH,
                _PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN,
                _EXTRA_KEY: {},
            }
        })
        db = AsyncMock()
        phase = await service.mark_resume_in_progress(_PROJECT_ID, db)
        assert phase == PHASE_RESEARCH
        sync.assert_awaited_once_with(
            db,
            _PROJECT_ID,
            {
                _CURRENT_PHASE_KEY: PHASE_RESEARCH,
                _PHASE_STATUS_KEY: PHASE_STATUS_IN_PROGRESS,
                _EXTRA_KEY: {},
                _PROJECT_ID_KEY: _PROJECT_ID,
            },
        )
        phase_change.assert_awaited_once_with(
            _PROJECT_ID, PHASE_RESEARCH, PHASE_STATUS_IN_PROGRESS
        )
        run_started.assert_awaited_once_with(db, _PROJECT_ID, PHASE_RESEARCH)

    async def test_state_without_a_phase_reports_an_empty_phase(
        self,
        service: EditorialWorkflowService,
        marking: tuple[AsyncMock, ...],
    ) -> None:
        sync, _run_started, _phase_change = marking
        with patch.object(
            service,
            _GET_WORKFLOW_STATE,
            new=AsyncMock(
                return_value={_PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN}
            ),
        ):
            phase = await service.mark_resume_in_progress(_PROJECT_ID, None)
        assert phase == ""
        synced = sync.await_args
        assert synced is not None
        assert synced.args[2][_CURRENT_PHASE_KEY] == ""


@pytest.mark.unit
class TestStartWorkflowExact:
    """Scenario: a fresh start seeds the stamped policy and asks for review."""

    async def test_policy_version_and_review_request_are_exact(
        self,
        service: EditorialWorkflowService,
        orchestrator: MagicMock,
        notifications: MagicMock,
    ) -> None:
        orchestrator.get_state = AsyncMock(return_value=None)
        orchestrator.enrich_research_sources = AsyncMock(return_value=[])
        orchestrator.synthesize_research = AsyncMock(return_value=[])
        orchestrator.start = AsyncMock(
            return_value={_CURRENT_PHASE_KEY: PHASE_RESEARCH}
        )
        orchestrator.update_state = AsyncMock()
        project = MagicMock()
        project.presentation_policy_version = _POLICY_VERSION
        db = AsyncMock()
        db.get = AsyncMock(return_value=project)
        with (
            patch(f"{_SERVICE}.CarouselProjectWriteOwner") as owner,
            patch(f"{_SERVICE}.emit_phase_event", new=AsyncMock()),
            patch(f"{_SERVICE}.publish_workflow_sse_updates", new=AsyncMock()),
        ):
            owner.return_value.assign_reviewer = AsyncMock()
            owner.return_value.sync_phase = AsyncMock()
            await service.start_workflow(
                _PROJECT_ID,
                EditorialWorkflowStartInput(
                    topic=_TOPIC,
                    audience="",
                    brief="",
                    sources=[],
                    user_id=_USER_ID,
                    reviewer_id=_REVIEWER_ID,
                ),
                db,
            )
        started = orchestrator.start.await_args
        assert started is not None
        assert started.kwargs[_POLICY_KEY] == _POLICY_VERSION
        notifications.create_review_request.assert_awaited_once_with(
            db,
            user_id=_REVIEWER_ID,
            content_id=_PROJECT_ID,
            content_type=CONTENT_TYPE_CAROUSEL,
            title=_TOPIC,
        )


@pytest.mark.unit
class TestStreamPhaseUpdates:
    """Scenario: the SSE stream forwards the caller's phase progress."""

    async def test_phase_progress_is_forwarded(
        self, service: EditorialWorkflowService
    ) -> None:
        seen: list[dict[str, object] | None] = []
        event: dict[str, object] = {_CURRENT_PHASE_KEY: PHASE_RESEARCH}

        async def fake_stream(
            _orchestrator: object,
            _project_id: str,
            *,
            phase_progress: dict[str, object] | None = None,
        ) -> AsyncIterator[dict[str, object]]:
            seen.append(phase_progress)
            yield event

        with patch(f"{_SERVICE}.stream_workflow_phase_updates", new=fake_stream):
            events = [
                item
                async for item in service.stream_phase_updates(
                    _PROJECT_ID, phase_progress=dict(_PROGRESS)
                )
            ]
        assert events == [event]
        assert seen == [_PROGRESS]
