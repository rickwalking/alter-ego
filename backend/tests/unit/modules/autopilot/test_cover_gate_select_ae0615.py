"""The drive asks for the succeeded autopilot cover at each gate before it resumes.

Gherkin: tests/features/autopilot_cover_gate_select_ae0615.feature
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
from rag_backend.modules.autopilot.constants import GATE_RESEARCH
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure import cover_autostart
from rag_backend.modules.autopilot.infrastructure.cover_autostart import (
    EditorialAutoCoverScheduler,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    SessionFactory,
)
from rag_backend.modules.editorial.public import REVIEW_ACTION_APPROVE
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
_IDLE_CAP = 30


@dataclass
class _Applier:
    """``AutoCoverApplier``: ``answers`` in order, then False; the resumes seen."""

    editorial: _Editorial
    answers: list[bool] = field(default_factory=list)
    calls: list[tuple[str, int]] = field(default_factory=list)

    async def apply_cover(self, project_id: str) -> bool:
        resumes = self.editorial.resumes or []
        self.calls.append((project_id, len(resumes)))
        return self.answers.pop(0) if self.answers else False


def _drive(applier_answers: list[bool]) -> tuple[AutopilotRunner, _Runs, _Applier]:
    run = _run(AutopilotRunState.GENERATING, project_id=_PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial()
    applier = _Applier(editorial=editorial, answers=applier_answers)
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=_Notices(),
            recovery=_Recovery(runs=runs),
            owner_user_id=_OWNER,
            inputs=FakeProjectInputs(),
            cover_apply=applier,
        )
    )
    return runner, runs, applier


async def _until_idle(runner: AutopilotRunner) -> int:
    for steps in range(_IDLE_CAP):
        if await runner.tick() == 0:
            return steps
    raise AssertionError("runner did not go idle")


@pytest.mark.unit
class TestRunnerCoverAtGate:
    # Scenario: The drive stores the cover at a gate before it resumes
    @pytest.mark.asyncio
    async def test_stored_cover_ends_the_step_before_any_resume(self) -> None:
        runner, _runs, applier = _drive([True])

        assert await runner.tick() == 1

        assert applier.calls == [(_PROJECT, 0)]
        assert applier.editorial.resumes == []

    # Scenario: The drive stores the cover at a gate before it resumes
    @pytest.mark.asyncio
    async def test_next_step_resumes_without_storing_twice(self) -> None:
        runner, runs, applier = _drive([True])

        await _until_idle(runner)

        resumes = applier.editorial.resumes or []
        assert runs.run.state is AutopilotRunState.AWAITING_OWNER
        assert [call[1] for call in applier.calls] == [0, 0, 1, 2, 3, 4]
        assert resumes[0].phase == GATE_RESEARCH
        assert resumes[0].action == REVIEW_ACTION_APPROVE
        assert len(resumes) == 5

    # Scenario: Without consent the drive stores nothing
    @pytest.mark.asyncio
    async def test_nothing_stored_resumes_as_before(self) -> None:
        runner, _runs, applier = _drive([])

        assert await runner.tick() == 1

        assert applier.calls == [(_PROJECT, 0)]
        assert len(applier.editorial.resumes or []) == 1


async def _selected(_sessions: SessionFactory, project_id: str) -> bool:
    return project_id == _PROJECT


@pytest.mark.unit
class TestSchedulerApplyCover:
    # Scenario: Without consent the drive stores nothing
    @pytest.mark.asyncio
    async def test_no_consent_never_selects(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: list[str] = []

        async def _select(_sessions: SessionFactory, project_id: str) -> bool:
            called.append(project_id)
            return True

        monkeypatch.setattr(cover_autostart, "select_cover_at_gate", _select)
        scheduler = EditorialAutoCoverScheduler(_no_sessions, consent=False)

        assert await scheduler.apply_cover(_PROJECT) is False
        assert called == []

    # Scenario: The drive stores the cover at a gate before it resumes
    @pytest.mark.asyncio
    async def test_consent_reports_the_selection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cover_autostart, "select_cover_at_gate", _selected)
        scheduler = EditorialAutoCoverScheduler(_no_sessions, consent=True)

        assert await scheduler.apply_cover(_PROJECT) is True
        assert await scheduler.apply_cover("other") is False

    # Scenario: A crash while storing the cover never breaks the drive
    @pytest.mark.asyncio
    async def test_crash_is_logged_and_reports_nothing_stored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _crash(_sessions: SessionFactory, _project_id: str) -> bool:
            raise RuntimeError("db down")

        monkeypatch.setattr(cover_autostart, "select_cover_at_gate", _crash)
        scheduler = EditorialAutoCoverScheduler(_no_sessions, consent=True)

        with capture_logs() as logs:
            assert await scheduler.apply_cover(_PROJECT) is False

        assert any(log.get("action") == "apply_cover" for log in logs)


def _no_sessions() -> AsyncSession:
    raise AssertionError("apply_cover opens no session of its own")
