"""The run heartbeat task never outlives the run that owns it.

CI "backend / Test & Coverage" hung ~3h at event-loop shutdown after every
test passed: the run wrapper cancelled its heartbeat task without waiting, so
a heartbeat caught inside a write was still pending when the loop closed.
"""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from unittest.mock import AsyncMock, patch

import pytest

from rag_backend.application.services.carousel import (
    editorial_workflow_run_heartbeat as run_heartbeat,
)
from rag_backend.application.services.carousel.editorial_workflow_resume_runner import (
    BackgroundResumeParams,
    execute_resume_run,
)
from rag_backend.domain.constants.carousel_workflow import REVIEW_ACTION_APPROVE
from rag_backend.domain.models.carousel_run import CarouselRunContext

_RUNNER = "rag_backend.application.services.carousel.editorial_workflow_resume_runner"
_PROJECT_ID = "ae0417-project"
_FENCE = CarouselRunContext(project_id=_PROJECT_ID, epoch=3)
_UNWIND_STEPS = 3


class _SlowWrite:
    """A heartbeat write that blocks, then needs loop turns to unwind a cancel.

    Models a DB write whose connection cleanup still awaits after the cancel
    lands (what SQLAlchemy does with the run's pooled connection).
    """

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.unwound = False

    async def __call__(self, project_id: str, epoch: int) -> bool:
        del project_id, epoch
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            for _ in range(_UNWIND_STEPS):
                await asyncio.sleep(0)
            self.unwound = True
            raise
        return True


def _params() -> BackgroundResumeParams:
    return BackgroundResumeParams(
        project_id=_PROJECT_ID,
        action=REVIEW_ACTION_APPROVE,
        reviewer_id="reviewer-1",
        feedback=None,
        project_title="Carousel",
        structured_feedback=None,
    )


@pytest.fixture
def slow_write(monkeypatch: pytest.MonkeyPatch) -> _SlowWrite:
    write = _SlowWrite()
    monkeypatch.setattr(run_heartbeat, "DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(run_heartbeat, "write_run_heartbeat_with_retry", write)
    return write


@pytest.mark.unit
class TestStopHeartbeat:
    """Scenario: stopping the heartbeat waits for an in-flight write to unwind."""

    async def test_stop_waits_for_the_write_to_finish(
        self, slow_write: _SlowWrite
    ) -> None:
        heartbeat = run_heartbeat.start_heartbeat(_FENCE)
        assert heartbeat is not None
        await slow_write.started.wait()

        await run_heartbeat.stop_heartbeat(heartbeat)

        assert heartbeat.done()
        assert heartbeat.cancelled()
        assert slow_write.unwound

    async def test_stop_without_a_heartbeat_is_a_no_op(self) -> None:
        await run_heartbeat.stop_heartbeat(None)

    async def test_cancel_of_the_caller_still_propagates(
        self, slow_write: _SlowWrite
    ) -> None:
        heartbeat = run_heartbeat.start_heartbeat(_FENCE)
        assert heartbeat is not None
        await slow_write.started.wait()
        caller = asyncio.create_task(run_heartbeat.stop_heartbeat(heartbeat))
        await asyncio.sleep(0)

        caller.cancel()

        with pytest.raises(asyncio.CancelledError):
            await caller
        await asyncio.wait((heartbeat,))


@pytest.mark.unit
class TestStartHeartbeat:
    """Scenario: only a run that owns a fence heartbeats."""

    def test_no_fence_starts_no_task(self) -> None:
        assert run_heartbeat.start_heartbeat(None) is None

    async def test_loop_ends_when_the_fence_is_lost(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write = AsyncMock(side_effect=[True, False])
        monkeypatch.setattr(run_heartbeat, "DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS", 0)
        monkeypatch.setattr(run_heartbeat, "write_run_heartbeat_with_retry", write)

        heartbeat = run_heartbeat.start_heartbeat(_FENCE)
        assert heartbeat is not None
        await heartbeat

        assert write.await_count == 2
        write.assert_awaited_with(_PROJECT_ID, _FENCE.epoch)


@pytest.mark.unit
class TestRunLeavesNoHeartbeatBehind:
    """Scenario: a finished run leaves no pending heartbeat task."""

    async def test_no_task_is_pending_after_the_run_returns(
        self, slow_write: _SlowWrite
    ) -> None:
        async def _run(*_args: object) -> None:
            await slow_write.started.wait()

        with (
            patch(f"{_RUNNER}.read_run_fence", new=AsyncMock(return_value=_FENCE)),
            patch(
                f"{_RUNNER}.open_run_trace_scope",
                new=AsyncMock(side_effect=lambda *_: nullcontext()),
            ),
            patch(f"{_RUNNER}._run_background_resume", new=_run),
        ):
            await execute_resume_run(AsyncMock(), _params())

        heartbeats = [
            task
            for task in asyncio.all_tasks()
            if task.get_coro().__qualname__
            == run_heartbeat.run_heartbeat_loop.__qualname__
        ]
        assert heartbeats == []
        assert slow_write.unwound
