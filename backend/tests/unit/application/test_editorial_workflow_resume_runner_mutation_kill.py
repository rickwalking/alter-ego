"""Exact-behaviour tests for the background editorial resume runner.

Feature: Carousel editorial workflow safety net (background resume)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    MarkFailedParams,
    _background_tasks,
    _execute_owned_run,
    _mark_background_resume_failed,
    _revert_background_resume_stuck,
    _run_background_resume,
    cancel_background_resume_task,
    detect_resume_stuck,
)
from rag_backend.domain.constants.carousel_run import (
    LOG_EVENT_RUN_FENCED,
    RUN_FINISHED_REASON_FAILED,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.models.carousel_run import StaleRunEpochError

_RUNNER = "rag_backend.application.services.carousel.editorial_workflow_resume_runner"
_PROJECT_ID = "proj-77"
_OTHER_PROJECT_ID = "proj-88"
_TASK_PREFIX = "workflow-resume-"
_SENTINEL_PHASES = ("None", "XXXX")


def _params(action: str = REVIEW_ACTION_APPROVE) -> BackgroundResumeParams:
    return BackgroundResumeParams(
        project_id=_PROJECT_ID,
        action=action,
        reviewer_id="reviewer-1",
        feedback=None,
        project_title="Carousel",
        structured_feedback=None,
    )


def _task(name: str, *, done: bool) -> MagicMock:
    task = MagicMock()
    task.get_name = MagicMock(return_value=name)
    task.done = MagicMock(return_value=done)
    return task


@pytest.fixture(autouse=True)
def _clean_background_tasks() -> Iterator[None]:
    _background_tasks.clear()
    yield
    _background_tasks.clear()


@pytest.fixture
def run_finished() -> Iterator[AsyncMock]:
    @asynccontextmanager
    async def fake_session() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    with (
        patch(f"{_RUNNER}.get_session_maker", return_value=fake_session),
        patch(f"{_RUNNER}.CarouselProjectWriteOwner") as owner,
        patch(f"{_RUNNER}.publish_run_finished", new=AsyncMock()) as finished,
    ):
        owner.return_value.set_phase_status_and_commit = AsyncMock()
        yield finished


@pytest.mark.unit
class TestCancelBackgroundResumeTask:
    """Scenario: the reaper cancels only the live task for its project."""

    def test_cancels_matching_live_task(self) -> None:
        target = _task(f"{_TASK_PREFIX}{_PROJECT_ID}", done=False)
        _background_tasks.add(target)
        assert cancel_background_resume_task(_PROJECT_ID) is True
        target.cancel.assert_called_once_with()

    def test_ignores_other_project_live_task(self) -> None:
        other = _task(f"{_TASK_PREFIX}{_OTHER_PROJECT_ID}", done=False)
        _background_tasks.add(other)
        assert cancel_background_resume_task(_PROJECT_ID) is False
        other.cancel.assert_not_called()

    def test_ignores_matching_finished_task(self) -> None:
        finished = _task(f"{_TASK_PREFIX}{_PROJECT_ID}", done=True)
        _background_tasks.add(finished)
        assert cancel_background_resume_task(_PROJECT_ID) is False
        finished.cancel.assert_not_called()

    def test_no_tasks_returns_false(self) -> None:
        assert cancel_background_resume_task(_PROJECT_ID) is False


@pytest.mark.unit
class TestExecuteOwnedRunFenced:
    """Scenario: a reaped (fenced) zombie run logs and stops."""

    async def test_stale_epoch_logs_fenced_event_with_project(self) -> None:
        with (
            patch(f"{_RUNNER}.read_run_fence", new=AsyncMock(return_value=None)),
            patch(f"{_RUNNER}.start_heartbeat", return_value=None),
            patch(f"{_RUNNER}.stop_heartbeat", new=AsyncMock()),
            patch(
                f"{_RUNNER}._run_background_resume",
                new=AsyncMock(side_effect=StaleRunEpochError(_PROJECT_ID)),
            ),
            patch(f"{_RUNNER}.logger") as logger,
        ):
            await _execute_owned_run(MagicMock(), _params())
        logger.warning.assert_called_once_with(
            LOG_EVENT_RUN_FENCED, project_id=_PROJECT_ID
        )


@pytest.mark.unit
class TestDetectResumeStuckMissingPhase:
    """Scenario: an approve with no phase in the new state is not stuck."""

    @pytest.mark.parametrize("prior_phase", _SENTINEL_PHASES)
    def test_missing_current_phase_never_matches_prior(self, prior_phase: str) -> None:
        state: dict[str, object] = {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
        assert detect_resume_stuck(_params(), prior_phase, state) is False


@pytest.mark.unit
class TestRunFinishedOnFailurePaths:
    """Scenario: stuck and failed resumes close the run with exact events."""

    async def test_stuck_revert_publishes_failed_awaiting_human(
        self, run_finished: AsyncMock
    ) -> None:
        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()
        await _revert_background_resume_stuck(service, _PROJECT_ID, "content")
        run_finished.assert_awaited_once_with(
            _PROJECT_ID,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

    async def test_mark_failed_publishes_failed_failed(
        self, run_finished: AsyncMock
    ) -> None:
        service = MagicMock()
        service.publish_resume_error_event = AsyncMock()
        await _mark_background_resume_failed(
            MarkFailedParams(
                service=service,
                project_id=_PROJECT_ID,
                message=ERR_BACKGROUND_RESUME_FAILED,
                recoverable=True,
            )
        )
        run_finished.assert_awaited_once_with(
            _PROJECT_ID,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_FAILED,
        )


@pytest.mark.unit
class TestBackgroundResumePriorPhaseFallback:
    """Scenario: a prior state without a phase is treated as having an empty phase."""

    async def test_prior_state_without_phase_passes_empty_prior_phase(self) -> None:
        @asynccontextmanager
        async def fake_session() -> AsyncIterator[AsyncMock]:
            yield AsyncMock()

        service = MagicMock()
        service.get_workflow_state = AsyncMock(
            return_value={"phase_status": PHASE_STATUS_AWAITING_HUMAN}
        )
        with (
            patch(f"{_RUNNER}.get_session_maker", return_value=fake_session),
            patch(f"{_RUNNER}.carousel_run_epoch_var") as epoch_var,
            patch(f"{_RUNNER}._run_phase", new=AsyncMock(return_value={})),
            patch(f"{_RUNNER}.detect_resume_stuck", return_value=False) as detect,
            patch(f"{_RUNNER}.CarouselProjectWriteOwner") as owner,
            patch(f"{_RUNNER}.publish_workflow_sse_updates", new=AsyncMock()),
            patch(f"{_RUNNER}.publish_run_finished", new=AsyncMock()),
        ):
            epoch_var.get.return_value = None
            owner.return_value.commit = AsyncMock()
            await _run_background_resume(service, _params())
        assert detect.call_args.args[1] == ""
