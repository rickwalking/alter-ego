"""Autopilot cover auto-selection: the background task and its wiring.

Gherkin: tests/features/autopilot_cover_autoselect_ae0590.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.application.services.carousel import (
    cover_generation_tasks,
    owner_autofix_lock,
)
from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverWrite,
    CoverBaseline,
)
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
    HookPhotoCommand,
)
from rag_backend.application.services.carousel.owner_autofix_lock import (
    AutofixConflictError,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_CRASHED,
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
)
from rag_backend.domain.models import CarouselProject, User, UserRole
from rag_backend.domain.models.cover_generation import CoverGenerationStatus
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)
from rag_backend.modules.editorial.infrastructure import (
    carousel_cover_autoselect,
    carousel_cover_autostart,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autoselect import (
    with_cover_selection,
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

        task = with_cover_selection(
            _generate(CoverGenerationStatus.SUCCEEDED), _SELECTION
        )

        assert await task() is CoverGenerationStatus.SUCCEEDED
        assert selector.selected == [_SELECTION]

    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_failure_never_selects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selector = _Selector()
        _install(monkeypatch, selector)

        task = with_cover_selection(_generate(CoverGenerationStatus.FAILED), _SELECTION)

        assert await task() is CoverGenerationStatus.FAILED
        assert selector.selected == []

    @pytest.mark.asyncio
    async def test_selection_crash_is_logged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        selector = _Selector(error=RuntimeError("db down"))
        _install(monkeypatch, selector)
        task = with_cover_selection(
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
            carousel_cover_autoselect, "cover_generation_task", lambda _w, _r: "gen"
        )

        def _wrap(generate: object, selection: AutoCoverSelection) -> object:
            wrapped.append((generate, selection))
            return "wrapped"

        monkeypatch.setattr(carousel_cover_autoselect, "with_cover_selection", _wrap)
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


@pytest.mark.unit
class TestLockedStore:
    """The write's outcomes with the lock and the database faked."""

    @staticmethod
    def _store() -> carousel_cover_autoselect._CoverStore:
        return carousel_cover_autoselect._CoverStore(
            command=AutoCoverWrite(
                project_id="p-1",
                asset_id=uuid4(),
                expected_version=3,
                baseline=_SELECTION.baseline,
            ),
            cover=SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="c.webp"),
        )

    # Scenario: A lock-version conflict is skipped and logged, never retried
    @pytest.mark.asyncio
    async def test_conflict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _locked(_db: object, _target: object, _write: object) -> bool:
            raise AutofixConflictError

        monkeypatch.setattr(owner_autofix_lock, "write_locked", _locked)

        found = await carousel_cover_autoselect._locked_store(
            cast(AsyncSession, object()), self._store()
        )

        assert found == AUTOFIX_STATUS_CONFLICT

    # Scenario: An owner photo bound while the write runs is kept
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("stored", "status"),
        [(True, AUTOFIX_STATUS_FIXED), (False, REASON_AUTO_SELECT_MANUAL_CHOICE)],
    )
    async def test_stored_or_moved(
        self, monkeypatch: pytest.MonkeyPatch, stored: bool, status: str
    ) -> None:
        async def _locked(_db: object, _target: object, _write: object) -> bool:
            return stored

        monkeypatch.setattr(owner_autofix_lock, "write_locked", _locked)

        found = await carousel_cover_autoselect._locked_store(
            cast(AsyncSession, object()), self._store()
        )

        assert found == status

    # Scenario: A generated cover whose file is gone is skipped
    @pytest.mark.asyncio
    async def test_unstageable_cover_is_asset_gone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = CarouselProject(topic="T", audience="A", niche="N")
        command = AutoCoverWrite(
            project_id=str(project.id),
            asset_id=uuid4(),
            expected_version=3,
            baseline=CoverBaseline(slide_cover_asset_id=None, hook_asset_id=None),
        )

        class _Acl:
            def __init__(self, _session: object) -> None: ...

            async def load_project(self, _project_id: str) -> CarouselProject:
                return project

        async def _asset(_session: object, _command: object) -> object:
            return _AssetRow(id=command.asset_id, relative_path="c.webp")

        async def _stage(_session: object, _target: object) -> bool:
            return False

        from rag_backend.modules.editorial.infrastructure import carousel_automation

        monkeypatch.setattr(carousel_automation, "CarouselAutomationAcl", _Acl)
        monkeypatch.setattr(carousel_cover_autoselect, "_generated_asset", _asset)
        monkeypatch.setattr(carousel_cover_autoselect, "_stage", _stage)

        found = await carousel_cover_autoselect._write(
            cast(AsyncSession, object()), command
        )

        assert found == REASON_AUTO_SELECT_ASSET_GONE


@dataclass(frozen=True)
class _AssetRow:
    id: object
    relative_path: str


@pytest.mark.unit
class TestHookPhotoClearsCover:
    # Scenario: Binding a slide-1 photo clears an auto-selected cover
    @pytest.mark.asyncio
    async def test_select_hook_photo_clears_slide_cover(self, tmp_path: Path) -> None:
        photo = _AssetRow(id=uuid4(), relative_path="p.webp")
        project = CarouselProject(topic="T", audience="A", niche="N")
        project.slide_cover = SlideCover(
            asset_id=uuid4(), kind="ai_image", staged_path="c.webp"
        )
        saved: list[CarouselProject] = []

        class _Assets:
            async def get_by_id(self, _asset_id: object) -> _AssetRow:
                return photo

        class _Projects:
            async def update_project(self, item: CarouselProject) -> CarouselProject:
                saved.append(item)
                return item

        service = CreatorAssetService(
            cast(PostgresCreatorAssetRepository, _Assets()),
            cast(CarouselRepository, _Projects()),
            tmp_path,
        )
        service.stage_into_candidate_artifact = lambda _c: None
        admin = User(
            email="a@x.test", full_name="A", role=UserRole.ADMIN, hashed_password="x"
        )

        await service.select_hook_photo(
            HookPhotoCommand(
                project=project,
                user=admin,
                creator_asset_id=photo.id,
                output_root=tmp_path,
            )
        )

        assert saved[0].slide_cover is None
        assert saved[0].hook_asset_id == photo.id
