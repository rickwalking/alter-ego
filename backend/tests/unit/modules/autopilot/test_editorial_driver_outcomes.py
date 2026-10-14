"""Provider and lock outcomes of the in-process editorial driver (AE-0354)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

from rag_backend.domain.constants.carousel_workflow import ERR_REVISION_CAP_EXCEEDED
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.modules.autopilot.domain.gate import (
    ProjectSpec,
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


class _Review:
    def __init__(self, error: BaseException, on_bump: bool) -> None:
        self._error = error
        self._on_bump = on_bump
        self.decisions = 0

    async def bump_resume_lock_version(self, project_id: str, version: int) -> None:
        if self._on_bump:
            raise self._error

    async def record_review_decision(self, payload: object) -> None:
        self.decisions += 1
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
    review = _Review(ValueError(ERR_VERSION_CONFLICT), on_bump=True)
    monkeypatch.setattr(editorial_driver, "_service", lambda *_args: review)
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
    assert review.decisions == 0
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_revision_cap_and_resume_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    capped = _Review(ValueError(ERR_REVISION_CAP_EXCEEDED), on_bump=False)
    monkeypatch.setattr(editorial_driver, "_service", lambda *_args: capped)
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
    assert capped.decisions == 1

    down = _Review(_api_error(), on_bump=False)
    monkeypatch.setattr(editorial_driver, "_service", lambda *_args: down)
    outage = await driver.resume(command)
    assert outage.status is ResumeStatus.PROVIDER_OUTAGE
    session.rollback.assert_awaited_once()
