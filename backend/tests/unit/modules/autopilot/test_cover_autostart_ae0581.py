"""Autopilot auto-cover: the consent gate and the runner hook.

Gherkin: tests/features/autopilot_cover_autostart_ae0581.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.domain.gate import StartStatus
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.cover_autostart import (
    EditorialAutoCoverScheduler,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autostart import (
    AutoCoverOutcome,
)
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _Editorial,
    _Notices,
    _Recovery,
    _run,
    _Runs,
    _topic,
)

_PROJECT = "22222222-2222-2222-2222-222222222222"
_OWNER = "owner-1"


@pytest.mark.unit
class TestEditorialAutoCoverScheduler:
    # Scenario: Without consent no photo is read or sent
    @pytest.mark.asyncio
    async def test_no_consent_skips_before_photos(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        called: list[str] = []

        async def _facade(_session: object, project_id: str) -> AutoCoverOutcome:
            called.append(project_id)
            return AutoCoverOutcome(scheduled=True, generation_id="g")

        monkeypatch.setattr(
            "rag_backend.modules.autopilot.infrastructure.cover_autostart.schedule_autopilot_cover",
            _facade,
        )
        scheduler = EditorialAutoCoverScheduler(
            lambda: _SessionCtx(db_session), consent=False
        )

        with capture_logs() as logs:
            await scheduler.start_cover(_PROJECT)

        assert called == []
        assert any(
            log.get("reason") == "no_consent" and log.get("outcome") == "auto_skipped"
            for log in logs
        )

    @pytest.mark.asyncio
    async def test_consent_calls_the_facade(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        called: list[str] = []

        async def _facade(_session: object, project_id: str) -> AutoCoverOutcome:
            called.append(project_id)
            return AutoCoverOutcome(scheduled=True, generation_id="g-1")

        monkeypatch.setattr(
            "rag_backend.modules.autopilot.infrastructure.cover_autostart.schedule_autopilot_cover",
            _facade,
        )
        scheduler = EditorialAutoCoverScheduler(
            lambda: _SessionCtx(db_session), consent=True
        )

        with capture_logs() as logs:
            await scheduler.start_cover(_PROJECT)

        assert called == [_PROJECT]
        assert any(log.get("outcome") == "auto_started" for log in logs)

    @pytest.mark.asyncio
    async def test_facade_crash_is_a_logged_skip(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        async def _facade(_session: object, project_id: str) -> AutoCoverOutcome:
            raise RuntimeError("db down")

        monkeypatch.setattr(
            "rag_backend.modules.autopilot.infrastructure.cover_autostart.schedule_autopilot_cover",
            _facade,
        )
        scheduler = EditorialAutoCoverScheduler(
            lambda: _SessionCtx(db_session), consent=True
        )

        with capture_logs() as logs:
            await scheduler.start_cover(_PROJECT)

        assert any(log.get("outcome") == "auto_skipped" for log in logs)


class _SessionCtx:
    """An async-context wrapper that never closes the shared test session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


@dataclass
class _AutoCover:
    calls: list[str] = field(default_factory=list)
    error: Exception | None = None

    async def start_cover(self, project_id: str) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append(project_id)


def _runner_with_cover(auto_cover: _AutoCover | None) -> tuple[AutopilotRunner, _Runs]:
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=_Editorial(),
            notices=_Notices(),
            recovery=_Recovery(runs=runs),
            owner_user_id=_OWNER,
            inputs=FakeProjectInputs(),
            auto_cover=auto_cover,
        )
    )
    return runner, runs


@pytest.mark.unit
class TestRunnerAutoCover:
    # Scenario: A fresh autopilot carousel gets one cover job
    @pytest.mark.asyncio
    async def test_fresh_start_schedules_one_cover(self) -> None:
        auto_cover = _AutoCover()
        runner, _runs = _runner_with_cover(auto_cover)

        assert await runner.tick() == 1

        assert auto_cover.calls == ["11111111-1111-1111-1111-111111111111"]

    # Scenario: A retried start still gets its cover
    @pytest.mark.asyncio
    async def test_attached_project_delegates_dedup(self) -> None:
        auto_cover = _AutoCover()
        run = _run(AutopilotRunState.QUEUED, project_id=_PROJECT)
        runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
        runner = AutopilotRunner(
            RunnerDependencies(
                runs=runs,
                topics=runs,
                editorial=_Editorial(),
                notices=_Notices(),
                recovery=_Recovery(runs=runs),
                owner_user_id=_OWNER,
                inputs=FakeProjectInputs(),
                auto_cover=auto_cover,
            )
        )

        await runner.tick()

        assert auto_cover.calls == [_PROJECT]

    # Scenario: A failed start never schedules a cover
    @pytest.mark.asyncio
    async def test_provider_outage_skips_the_cover(self) -> None:
        auto_cover = _AutoCover()
        run = _run(AutopilotRunState.QUEUED)
        runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
        runner = AutopilotRunner(
            RunnerDependencies(
                runs=runs,
                topics=runs,
                editorial=_Editorial(start_status=StartStatus.PROVIDER_OUTAGE),
                notices=_Notices(),
                recovery=_Recovery(runs=runs),
                owner_user_id=_OWNER,
                inputs=FakeProjectInputs(),
                auto_cover=auto_cover,
            )
        )

        await runner.tick()

        assert auto_cover.calls == []
        assert runs.run.start_attempts == 1

    # Scenario: A cover failure never fails the run
    @pytest.mark.asyncio
    async def test_cover_error_keeps_the_run_generating(self) -> None:
        auto_cover = _AutoCover(error=RuntimeError("bridge down"))
        runner, runs = _runner_with_cover(auto_cover)

        await runner.tick()

        assert runs.run.state is AutopilotRunState.GENERATING
