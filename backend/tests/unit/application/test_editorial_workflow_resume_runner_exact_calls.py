"""Exact run-ownership calls made by the background editorial resume runner.

Feature: Carousel editorial workflow safety net (background resume run ownership)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, nullcontext
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    _beat_and_stage,
    _execute_owned_run,
    _run_background_resume,
    execute_resume_run,
)
from rag_backend.domain.constants.carousel_run import (
    LOG_EVENT_RUN_FENCED,
    RUN_FINISHED_REASON_COMPLETED,
    RUN_STAGE_GENERATING,
    RUN_STAGE_PERSISTING,
    RUN_STAGE_VALIDATING,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    StaleRunEpochError,
    carousel_run_epoch_var,
)

_RUNNER = "rag_backend.application.services.carousel.editorial_workflow_resume_runner"
_PROJECT_ID = "proj-runner-9"
_REVIEWER_ID = "reviewer-12"
_EPOCH = 7
_BOUNDED_WAIT_SECONDS = 1.0
_CURRENT_PHASE_KEY = "current_phase"
_PHASE_STATUS_KEY = "phase_status"
_LOG_CANCELLED = "background_resume_cancelled"


def _params() -> BackgroundResumeParams:
    return BackgroundResumeParams(
        project_id=_PROJECT_ID,
        action=REVIEW_ACTION_APPROVE,
        reviewer_id=_REVIEWER_ID,
        feedback=None,
        project_title="Carousel",
        structured_feedback=None,
    )


def _context() -> CarouselRunContext:
    return CarouselRunContext(project_id=_PROJECT_ID, epoch=_EPOCH)


@pytest.mark.unit
class TestExecuteResumeRunTraceScope:
    """Scenario: the run is traced under its project and its reviewer."""

    async def test_trace_scope_gets_project_and_reviewer(self) -> None:
        scope = AsyncMock(return_value=nullcontext())
        with (
            patch(f"{_RUNNER}.open_run_trace_scope", new=scope),
            patch(f"{_RUNNER}._execute_owned_run", new=AsyncMock()) as owned,
            patch(f"{_RUNNER}.flush_workflow_traces") as flush,
        ):
            await asyncio.wait_for(
                execute_resume_run(MagicMock(), _params()), _BOUNDED_WAIT_SECONDS
            )
        scope.assert_awaited_once_with(_PROJECT_ID, _REVIEWER_ID)
        owned.assert_awaited_once()
        flush.assert_called_once_with()


@pytest.mark.unit
class TestExecuteOwnedRunFence:
    """Scenario: the run captures its fence and heartbeats with it."""

    async def test_fence_is_bound_during_the_run_and_the_heartbeat_stopped(
        self,
    ) -> None:
        fence = _context()
        heartbeat = MagicMock()
        seen: list[CarouselRunContext | None] = []

        async def run(_service: object, _params: object) -> None:
            seen.append(carousel_run_epoch_var.get())

        with (
            patch(
                f"{_RUNNER}.read_run_fence", new=AsyncMock(return_value=fence)
            ) as read_fence,
            patch(f"{_RUNNER}.start_heartbeat", return_value=heartbeat) as start,
            patch(f"{_RUNNER}.stop_heartbeat", new=AsyncMock()) as stop,
            patch(f"{_RUNNER}._run_background_resume", new=run),
        ):
            await asyncio.wait_for(
                _execute_owned_run(MagicMock(), _params()), _BOUNDED_WAIT_SECONDS
            )
        read_fence.assert_awaited_once_with(_PROJECT_ID)
        start.assert_called_once_with(fence)
        stop.assert_awaited_once_with(heartbeat)
        assert seen == [fence]
        assert carousel_run_epoch_var.get() is None


@pytest.mark.unit
class TestBeatAndStage:
    """Scenario: a stage boundary publishes the stage and beats the run's epoch."""

    async def test_stage_and_heartbeat_use_the_run_context(self) -> None:
        with (
            patch(f"{_RUNNER}.publish_run_stage_changed", new=AsyncMock()) as stage,
            patch(f"{_RUNNER}.write_run_heartbeat_once", new=AsyncMock()) as beat,
        ):
            await _beat_and_stage(_context(), RUN_STAGE_VALIDATING)
        stage.assert_awaited_once_with(_PROJECT_ID, RUN_STAGE_VALIDATING)
        beat.assert_awaited_once_with(_PROJECT_ID, _EPOCH)


@dataclass
class _RunDoubles:
    """Collaborator doubles of one background resume run."""

    beat: AsyncMock
    run_phase: AsyncMock
    finished: AsyncMock
    mark_failed: AsyncMock
    logger: MagicMock
    service: MagicMock


@pytest.fixture
def run_doubles() -> Iterator[_RunDoubles]:
    @asynccontextmanager
    async def fake_session() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    service = MagicMock()
    service.get_workflow_state = AsyncMock(
        return_value={_CURRENT_PHASE_KEY: PHASE_RESEARCH}
    )
    token = carousel_run_epoch_var.set(_context())
    try:
        with (
            patch(f"{_RUNNER}.get_session_maker", return_value=fake_session),
            patch(f"{_RUNNER}.CarouselProjectWriteOwner") as owner,
            patch(f"{_RUNNER}.publish_workflow_sse_updates", new=AsyncMock()),
            patch(f"{_RUNNER}.publish_run_finished", new=AsyncMock()) as finished,
            patch(f"{_RUNNER}._beat_and_stage", new=AsyncMock()) as beat,
            patch(f"{_RUNNER}._run_phase", new=AsyncMock()) as run_phase,
            patch(
                f"{_RUNNER}._mark_background_resume_failed", new=AsyncMock()
            ) as mark_failed,
            patch(f"{_RUNNER}.logger") as logger,
        ):
            owner.return_value.commit = AsyncMock()
            yield _RunDoubles(
                beat=beat,
                run_phase=run_phase,
                finished=finished,
                mark_failed=mark_failed,
                logger=logger,
                service=service,
            )
    finally:
        carousel_run_epoch_var.reset(token)


async def _run(doubles: _RunDoubles) -> None:
    await asyncio.wait_for(
        _run_background_resume(doubles.service, _params()), _BOUNDED_WAIT_SECONDS
    )


@pytest.mark.unit
class TestBackgroundResumeCompletion:
    """Scenario: a completed resume walks every stage and closes the run."""

    async def test_every_stage_is_beaten_with_the_run_context(
        self, run_doubles: _RunDoubles
    ) -> None:
        run_doubles.run_phase.return_value = {
            _CURRENT_PHASE_KEY: PHASE_OUTLINE,
            _PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN,
        }
        await _run(run_doubles)
        context = _context()
        assert run_doubles.beat.await_args_list == [
            call(context, RUN_STAGE_GENERATING),
            call(context, RUN_STAGE_VALIDATING),
            call(context, RUN_STAGE_PERSISTING),
        ]

    async def test_run_finished_carries_the_final_phase_status(
        self, run_doubles: _RunDoubles
    ) -> None:
        run_doubles.run_phase.return_value = {
            _CURRENT_PHASE_KEY: PHASE_OUTLINE,
            _PHASE_STATUS_KEY: PHASE_STATUS_AWAITING_HUMAN,
        }
        await _run(run_doubles)
        run_doubles.finished.assert_awaited_once_with(
            _PROJECT_ID,
            RUN_FINISHED_REASON_COMPLETED,
            final_phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

    async def test_run_finished_without_a_status_reports_an_empty_status(
        self, run_doubles: _RunDoubles
    ) -> None:
        run_doubles.run_phase.return_value = {_CURRENT_PHASE_KEY: PHASE_OUTLINE}
        await _run(run_doubles)
        run_doubles.finished.assert_awaited_once_with(
            _PROJECT_ID,
            RUN_FINISHED_REASON_COMPLETED,
            final_phase_status="",
        )


@pytest.mark.unit
class TestBackgroundResumeCancelledWhileFenced:
    """Scenario: a cancelled, already-reaped run logs the fence and re-raises."""

    async def test_fenced_mark_failed_logs_and_cancellation_propagates(
        self, run_doubles: _RunDoubles
    ) -> None:
        run_doubles.run_phase.side_effect = asyncio.CancelledError()
        run_doubles.mark_failed.side_effect = StaleRunEpochError(_PROJECT_ID)
        with pytest.raises(asyncio.CancelledError):
            await _run(run_doubles)
        assert run_doubles.logger.warning.call_args_list == [
            call(_LOG_CANCELLED, project_id=_PROJECT_ID),
            call(LOG_EVENT_RUN_FENCED, project_id=_PROJECT_ID),
        ]
        run_doubles.finished.assert_not_awaited()
