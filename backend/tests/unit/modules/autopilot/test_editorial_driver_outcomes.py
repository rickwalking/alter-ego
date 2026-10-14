"""Provider and lock outcomes of the in-process editorial driver (AE-0354, AE-0363)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

from rag_backend.domain.constants.carousel_workflow import (
    ERR_NOTHING_TO_REDRIVE,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISION_CAP_EXCEEDED,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.modules.autopilot.domain.gate import (
    ProjectSpec,
    RedriveCommand,
    ResumeCommand,
    ResumeStatus,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.infrastructure import editorial_driver
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    EditorialDriverConfig,
    InProcessEditorialDriver,
)
from rag_backend.modules.editorial.public import AutomationRun

_PROJECT = "11111111-1111-1111-1111-111111111111"


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 10, 13, tzinfo=UTC)


def _spec() -> ProjectSpec:
    return ProjectSpec(
        topic="Agents",
        audience="builders",
        niche="ai",
        brief="brief",
        sources=("https://example.com",),
        owner_user_id="owner-1",
    )


def _api_error() -> openai.APIError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat")
    return openai.APIError("down", request, body=None)


def _driver(session: AsyncMock) -> InProcessEditorialDriver:
    return InProcessEditorialDriver(
        EditorialDriverConfig(
            session=session,
            engine_factory=MagicMock,
            clock=_Clock(),
            stale_after_seconds=180,
        )
    )


class _StartBoom:
    async def start(self, engine: object, workflow: object) -> None:
        raise _api_error()


class _Operation:
    """Stands in for the run-owned facade operation (AE-0363)."""

    def __init__(self, error: BaseException | None = None) -> None:
        self._error = error
        self.runs: list[object] = []

    async def __call__(self, run: object) -> None:
        self.runs.append(run)
        if self._error is not None:
            raise self._error


@pytest.mark.asyncio
async def test_start_provider_outage_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    monkeypatch.setattr(editorial_driver, "_handlers", lambda _session: _StartBoom())
    status = await _driver(session).start(
        StartCommand(project_id=_PROJECT, spec=_spec(), phase="research")
    )
    assert status is StartStatus.PROVIDER_OUTAGE
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_version_conflict_does_not_resume_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    operation = _Operation(ValueError(ERR_VERSION_CONFLICT))
    monkeypatch.setattr(editorial_driver, "run_automation_phase", operation)
    result = await _driver(session).resume(
        ResumeCommand(
            project_id=_PROJECT,
            action="approve",
            expected_version=2,
            feedback="",
            phase="research",
        )
    )
    assert result.status is ResumeStatus.VERSION_CONFLICT
    assert len(operation.runs) == 1
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_target_phase_is_structured_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rework feedback names the phase the editorial revise should reopen."""
    session = AsyncMock()
    operation = _Operation()
    monkeypatch.setattr(editorial_driver, "run_automation_phase", operation)
    result = await _driver(session).resume(
        ResumeCommand(
            project_id=_PROJECT,
            action="revise",
            expected_version=4,
            feedback="darker palette",
            phase="final_review",
            target_phase="images",
        )
    )
    run = operation.runs[0]
    assert isinstance(run, AutomationRun)
    assert result.status is ResumeStatus.APPLIED
    assert run.structured_feedback == {"target_phase": "images"}
    assert run.expected_version == 4
    assert run.feedback == "darker palette"
    assert run.session is session


@pytest.mark.asyncio
async def test_revision_cap_and_resume_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    capped = _Operation(ValueError(ERR_REVISION_CAP_EXCEEDED))
    monkeypatch.setattr(editorial_driver, "run_automation_phase", capped)
    driver = _driver(session)
    command = ResumeCommand(
        project_id=_PROJECT,
        action="revise",
        expected_version=2,
        feedback="fix",
        phase="content",
    )
    capped_result = await driver.resume(command)
    assert capped_result.status is ResumeStatus.REVISION_CAP
    session.rollback.assert_not_awaited()

    down = _Operation(_api_error())
    monkeypatch.setattr(editorial_driver, "run_automation_phase", down)
    outage = await driver.resume(command)
    assert outage.status is ResumeStatus.PROVIDER_OUTAGE
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_in_flight_and_not_parked_are_refusals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AE-0363: a run in flight or nothing parked changes nothing."""
    session = AsyncMock()
    busy = _Operation(ValueError(ERR_RESUME_ALREADY_IN_PROGRESS))
    monkeypatch.setattr(editorial_driver, "run_automation_phase", busy)
    driver = _driver(session)
    result = await driver.resume(
        ResumeCommand(
            project_id=_PROJECT,
            action="approve",
            expected_version=3,
            feedback="",
            phase="outline",
        )
    )
    assert result.status is ResumeStatus.IN_PROGRESS

    nothing = _Operation(ValueError(ERR_NOTHING_TO_REDRIVE))
    monkeypatch.setattr(editorial_driver, "redrive_automation_phase", nothing)
    redrive = await driver.redrive(
        RedriveCommand(project_id=_PROJECT, expected_version=3, phase="content")
    )
    assert redrive.status is ResumeStatus.NOT_PARKED
    run = nothing.runs[0]
    assert isinstance(run, AutomationRun)
    assert run.expected_version == 3
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_unclassified_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """An error the driver does not know reaches the runner's containment."""
    boom = _Operation(ValueError("something else"))
    monkeypatch.setattr(editorial_driver, "redrive_automation_phase", boom)
    with pytest.raises(ValueError, match="something else"):
        await _driver(AsyncMock()).redrive(
            RedriveCommand(project_id=_PROJECT, expected_version=1, phase="content")
        )
    crash = _Operation(RuntimeError("crash"))
    monkeypatch.setattr(editorial_driver, "run_automation_phase", crash)
    with pytest.raises(RuntimeError):
        await _driver(AsyncMock()).resume(
            ResumeCommand(
                project_id=_PROJECT,
                action="approve",
                expected_version=1,
                feedback="",
                phase="outline",
            )
        )
