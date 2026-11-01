"""Autopilot cover auto-selection: the background task and its wiring.

Gherkin: tests/features/autopilot_cover_autoselect_ae0590.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel import cover_generation_tasks
from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    CoverBaseline,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_CRASHED,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.modules.editorial.infrastructure import (
    carousel_cover_autoselect,
    carousel_cover_autostart,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    autopilot_cover_task,
)

_SELECTION = AutoCoverSelection(
    project_id="p-1",
    generation_id=uuid4(),
    baseline=CoverBaseline(slide_cover_asset_id=None, hook_asset_id=None),
)


@dataclass
class _Selector:
    selected: list[AutoCoverSelection] = field(default_factory=list)
    error: Exception | None = None

    async def select(self, selection: AutoCoverSelection) -> str:
        self.selected.append(selection)
        if self.error is not None:
            raise self.error
        return "selected"


def _generate(
    status: CoverGenerationStatus,
) -> Callable[[], Awaitable[CoverGenerationStatus]]:
    async def _run() -> CoverGenerationStatus:
        return status

    return _run


def _install(monkeypatch: pytest.MonkeyPatch, selector: _Selector) -> None:
    monkeypatch.setattr(
        carousel_cover_autoselect, "auto_cover_selector", lambda: selector
    )


@pytest.mark.unit
class TestAutopilotCoverTask:
    # Scenario: A succeeded autopilot cover becomes slide 1's cover
    @pytest.mark.asyncio
    async def test_success_runs_the_selection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        selector = _Selector()
        _install(monkeypatch, selector)

        task = autopilot_cover_task(
            _generate(CoverGenerationStatus.SUCCEEDED), _SELECTION
        )

        assert await task() is CoverGenerationStatus.SUCCEEDED
        assert selector.selected == [_SELECTION]

    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_failure_never_selects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selector = _Selector()
        _install(monkeypatch, selector)

        task = autopilot_cover_task(_generate(CoverGenerationStatus.FAILED), _SELECTION)

        assert await task() is CoverGenerationStatus.FAILED
        assert selector.selected == []

    @pytest.mark.asyncio
    async def test_selection_crash_is_logged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        selector = _Selector(error=RuntimeError("db down"))
        _install(monkeypatch, selector)
        task = autopilot_cover_task(
            _generate(CoverGenerationStatus.SUCCEEDED), _SELECTION
        )

        with capture_logs() as logs:
            assert await task() is CoverGenerationStatus.SUCCEEDED

        assert logs[-1]["event"] == LOG_COVER_AUTO_SELECT
        assert logs[-1]["outcome"] == OUTCOME_AUTO_SELECT_CRASHED


@dataclass(frozen=True)
class _Generation:
    id: object


@dataclass(frozen=True)
class _Run:
    generation: _Generation


@pytest.mark.unit
class TestScheduleWiring:
    # Scenario: A succeeded autopilot cover becomes slide 1's cover
    def test_schedules_the_wrapped_task_with_the_baseline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        hook = uuid4()
        project = CarouselProject(topic="T", audience="A", niche="N")
        project.hook_asset_id = hook
        wrapped: list[tuple[object, AutoCoverSelection]] = []
        scheduled: list[tuple[object, str]] = []
        generation_id = uuid4()

        monkeypatch.setattr(
            carousel_cover_autostart, "cover_generation_task", lambda _w, _r: "gen"
        )

        def _wrap(generate: object, selection: AutoCoverSelection) -> object:
            wrapped.append((generate, selection))
            return "wrapped"

        monkeypatch.setattr(carousel_cover_autostart, "autopilot_cover_task", _wrap)
        monkeypatch.setattr(
            cover_generation_tasks,
            "schedule_cover_generation",
            lambda task, gid: scheduled.append((task, gid)),
        )

        carousel_cover_autostart._schedule(
            object(),
            _Run(_Generation(generation_id)),
            project,
        )

        assert scheduled == [("wrapped", str(generation_id))]
        generate, selection = wrapped[0]
        assert generate == "gen"
        assert selection.project_id == str(project.id)
        assert selection.generation_id == generation_id
        assert selection.baseline == CoverBaseline(
            slide_cover_asset_id=None, hook_asset_id=hook
        )
