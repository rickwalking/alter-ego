"""The runner as the generation queue drives it: step, retryable errors, park."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_backend.modules.autopilot.application.runner import AutopilotRunner
from rag_backend.modules.autopilot.constants import GATE_CONTENT
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _PROJECT,
    _Notices,
    _run,
    _Runs,
    _topic,
)
from tests.unit.modules.autopilot.test_qa_r1_runner_recovery import _Raising, _runner


def _retrying(runner: AutopilotRunner) -> AutopilotRunner:
    deps = replace(runner._deps, retryable=lambda exc: isinstance(exc, TimeoutError))
    return AutopilotRunner(deps)


async def test_a_retryable_error_is_raised_for_the_queue() -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    runner, recovery = _runner(
        runs, _Raising(phase=GATE_CONTENT, error=TimeoutError("slow")), _Notices()
    )
    with pytest.raises(TimeoutError):
        await _retrying(runner).step(run)
    assert recovery.rollbacks == 1
    assert runs.run.state is AutopilotRunState.GENERATING


async def test_other_errors_are_still_contained() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    runner, _recovery = _runner(runs, _Raising(error=RuntimeError("boom")), _Notices())
    assert await _retrying(runner).step(run) == 1
    assert runs.run.state is AutopilotRunState.FAILED


@pytest.mark.parametrize(
    ("state", "parked"),
    [
        (AutopilotRunState.GENERATING, AutopilotRunState.ESCALATED),
        (AutopilotRunState.QUEUED, AutopilotRunState.FAILED),
        (AutopilotRunState.AWAITING_OWNER, AutopilotRunState.AWAITING_OWNER),
    ],
)
async def test_park_ends_an_active_run_with_the_queue_reason(
    state: AutopilotRunState, parked: AutopilotRunState
) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    run = _run(state, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    runner, _recovery = _runner(runs, _Raising(), _Notices())
    await runner.park(run, "queue_dead_letter:permanent")
    assert runs.run.state is parked
    if parked is not state:
        assert runs.run.state_reason == "queue_dead_letter:permanent"


async def test_sweep_is_the_recovery_sweep() -> None:
    """Scenario: One autopilot drive steps a run until the owner has to act"""
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=None)
    runner, _recovery = _runner(runs, _Raising(), _Notices())
    assert await runner.sweep() == 0
