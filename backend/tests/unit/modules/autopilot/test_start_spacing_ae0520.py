"""Autopilot generation starts are spaced (20 minutes by default).

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.constants.autopilot_start import (
    DEFAULT_START_SPACING_MINUTES,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.application.start_spacing import StartSpacing
from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    ProjectSpec,
    StartAttemptCommand,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.start_spacing import NO_WAIT, start_wait
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Notices,
    _Recovery,
    _run,
    _topic,
)

_OWNER = "owner-1"
_BATCH_AT = datetime(2026, 10, 22, 11, 5, tzinfo=UTC)
_SPACING = timedelta(minutes=DEFAULT_START_SPACING_MINUTES)
_SIMULATED_MINUTES = 90


@dataclass
class _Clock:
    at: datetime

    def now(self) -> datetime:
        return self.at


@dataclass
class _Board:
    """Several runs, the carousel creation time per run, and every start."""

    clock: _Clock
    runs: list[AutopilotRun]
    created: dict[UUID, datetime] = field(default_factory=dict)
    starts: list[datetime] = field(default_factory=list)

    def _put(self, run: AutopilotRun) -> None:
        self.runs = [run if r.run_id == run.run_id else r for r in self.runs]

    def find(self, run_id: UUID) -> AutopilotRun:
        return next(r for r in self.runs if r.run_id == run_id)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        return [r for r in self.runs if r.state is query.state][: query.limit]

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.find(run_id)

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        return _topic(candidate_id)

    async def attach_project(self, command: AttachProjectCommand) -> bool:
        self._put(
            replace(self.find(command.run_id), carousel_project_id=command.project_id)
        )
        self.created[command.run_id] = self.clock.now()
        return True

    async def note_start_attempt(self, command: StartAttemptCommand) -> bool:
        self._put(replace(self.find(command.run_id), start_attempts=command.attempts))
        return True

    async def transition(self, command: TransitionCommand) -> bool:
        run = self.find(command.run_id)
        if run.state is not command.expected:
            return False
        if command.new is AutopilotRunState.GENERATING:
            self.starts.append(self.clock.now())
        self._put(replace(run, state=command.new, state_reason=command.reason))
        return True

    async def latest_start(self, exclude_run: UUID) -> datetime | None:
        others = [at for run_id, at in self.created.items() if run_id != exclude_run]
        return max(others, default=None)

    def finish_generating(self) -> None:
        for run in self.runs:
            if run.state is AutopilotRunState.GENERATING:
                self._put(replace(run, state=AutopilotRunState.AWAITING_OWNER))


@dataclass
class _Editorial:
    start_status: StartStatus = StartStatus.STARTED
    created: int = 0
    started: int = 0

    async def create_project(self, spec: ProjectSpec) -> str:
        self.created += 1
        return str(uuid4())

    async def start(self, command: StartCommand) -> StartStatus:
        self.started += 1
        return self.start_status


def _runner(
    board: _Board, editorial: _Editorial, minimum: timedelta
) -> AutopilotRunner:
    return AutopilotRunner(
        RunnerDependencies(
            runs=board,
            topics=board,
            editorial=editorial,
            notices=_Notices(),
            recovery=_Recovery(),
            owner_user_id=_OWNER,
            inputs=FakeProjectInputs(),
            clock=board.clock,
            spacing=StartSpacing(starts=board, clock=board.clock, minimum=minimum),
        )
    )


def _queued_board(count: int, at: datetime = _BATCH_AT) -> _Board:
    return _Board(
        clock=_Clock(at), runs=[_run(AutopilotRunState.QUEUED) for _ in range(count)]
    )


@pytest.mark.asyncio
async def test_queued_run_waits_for_a_recent_start() -> None:
    """Scenario: A queued run waits until the previous start is 20 minutes old."""
    board = _queued_board(1)
    board.created[uuid4()] = _BATCH_AT - timedelta(minutes=5)
    editorial = _Editorial()

    stepped = await _runner(board, editorial, _SPACING).tick()

    assert stepped == 0
    assert editorial.created == 0
    assert board.runs[0].state is AutopilotRunState.QUEUED
    assert board.runs[0].carousel_project_id is None


@pytest.mark.asyncio
async def test_queued_run_starts_once_the_previous_start_is_old_enough() -> None:
    """Scenario: A queued run waits until the previous start is 20 minutes old."""
    board = _queued_board(1)
    board.created[uuid4()] = _BATCH_AT - _SPACING
    editorial = _Editorial()

    assert await _runner(board, editorial, _SPACING).tick() == 1

    assert board.runs[0].state is AutopilotRunState.GENERATING
    assert board.starts == [_BATCH_AT]


@pytest.mark.asyncio
async def test_three_runs_queued_at_1105_start_twenty_minutes_apart() -> None:
    """Scenario: Three runs queued at 11:05 start at least 20 minutes apart."""
    board = _queued_board(3)
    runner = _runner(board, _Editorial(), _SPACING)

    for minute in range(_SIMULATED_MINUTES):
        board.clock.at = _BATCH_AT + timedelta(minutes=minute)
        await runner.tick()
        board.finish_generating()

    assert len(board.starts) == 3
    assert board.starts[0] == _BATCH_AT
    gaps = [
        later - earlier
        for earlier, later in zip(board.starts, board.starts[1:], strict=False)
    ]
    assert gaps == [_SPACING, _SPACING]


@pytest.mark.asyncio
async def test_zero_spacing_starts_runs_back_to_back() -> None:
    """Scenario: Spacing 0 starts queued runs back to back."""
    board = _queued_board(1)
    board.created[uuid4()] = _BATCH_AT - timedelta(minutes=1)

    assert await _runner(board, _Editorial(), NO_WAIT).tick() == 1

    assert board.runs[0].state is AutopilotRunState.GENERATING


@pytest.mark.asyncio
async def test_failed_start_retries_without_waiting_for_itself() -> None:
    """Scenario: A run whose start failed retries without waiting for itself."""
    board = _queued_board(1)
    editorial = _Editorial(start_status=StartStatus.PROVIDER_OUTAGE)
    runner = _runner(board, editorial, _SPACING)
    await runner.tick()
    assert board.runs[0].carousel_project_id is not None
    assert board.runs[0].state is AutopilotRunState.QUEUED

    editorial.start_status = StartStatus.STARTED
    board.clock.at = _BATCH_AT + timedelta(minutes=1)
    assert await runner.tick() == 1

    assert editorial.created == 1
    assert editorial.started == 2
    assert board.runs[0].state is AutopilotRunState.GENERATING


def test_start_wait_is_the_rest_of_the_spacing() -> None:
    """Scenario: A queued run waits until the previous start is 20 minutes old."""
    latest = _BATCH_AT
    assert start_wait(None, _BATCH_AT, _SPACING) == NO_WAIT
    assert start_wait(latest, _BATCH_AT, NO_WAIT) == NO_WAIT
    assert start_wait(latest, _BATCH_AT + timedelta(minutes=5), _SPACING) == (
        timedelta(minutes=15)
    )
    assert start_wait(latest, _BATCH_AT + timedelta(minutes=45), _SPACING) == NO_WAIT


def test_start_spacing_setting_defaults_to_twenty_minutes() -> None:
    """Scenario: Three runs queued at 11:05 start at least 20 minutes apart."""
    assert DEFAULT_START_SPACING_MINUTES == 20
    assert Settings.model_fields["autopilot_start_spacing_minutes"].default == 20
