"""Publish-step slide-1 cover picker with fakes.

Gherkin: tests/features/carousel_cover_pick_ae0445.feature
  Scenario: The options are the owner's library photos, the current one marked
  Scenario: The GrokBot cover offer of the autopilot run is an option too
  Scenario: Choosing another library photo re-renders slide 1 from it
  Scenario: Choosing the GrokBot offer stores it as the slide-1 cover
  Scenario: A stale lock version is a conflict and writes nothing
  Scenario: An active workflow run is a conflict
  Scenario Outline: Refused choices
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from rag_backend.api.routes.carousels.cover_pick import _raise_unless_switched
from rag_backend.application.services.carousel import slide_cover_switch
from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickDeps,
    CoverPickError,
    CoverPickService,
    current_cover_asset,
)
from rag_backend.application.services.carousel.owner_autofix_lock import LockedWrite
from rag_backend.application.services.carousel.slide_cover_switch import (
    HookPhotoChoice,
    SlideCoverSwitchCommand,
    SlideCoverSwitchDeps,
    SlideCoverSwitchResult,
    SlideCoverSwitchService,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.slide_cover import SlideCover

_OWNER = "00000000-0000-4000-8000-000000000445"


def _photo(name: str) -> CarouselCreatorAsset:
    return CarouselCreatorAsset(
        owner_id=_OWNER,
        content_sha256=name,
        media_type="image/webp",
        width=1080,
        height=1350,
        relative_path=f"assets/creators/{name}.webp",
        role="hook",
    )


@dataclass
class _Library:
    items: tuple[CarouselCreatorAsset, ...]
    staged: list[UUID] = field(default_factory=list)
    asked: list[str] = field(default_factory=list)

    async def photos(self, owner_id: str) -> tuple[CarouselCreatorAsset, ...]:
        self.asked.append(owner_id)
        return self.items

    async def stage(
        self, project: CarouselProject, asset: CarouselCreatorAsset
    ) -> None:
        del project
        self.staged.append(asset.id)


@dataclass
class _Offers:
    cover: SlideCover | None = None

    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id
        return self.cover


@dataclass
class _Switcher:
    commands: list[SlideCoverSwitchCommand] = field(default_factory=list)

    async def switch(self, command: SlideCoverSwitchCommand) -> SlideCoverSwitchResult:
        self.commands.append(command)
        return SlideCoverSwitchResult(status="fixed")


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.owner_id = _OWNER
    project.content_mode = "pov"
    project.status = CarouselStatus.COMPLETED
    project.phase_status = "awaiting_human"
    for key, value in changes.items():
        setattr(project, key, value)
    return project


def _service(
    library: _Library, offers: _Offers | None = None
) -> tuple[CoverPickService, _Switcher]:
    switcher = _Switcher()
    deps = CoverPickDeps(library=library, offers=offers or _Offers(), switcher=switcher)
    return CoverPickService(deps), switcher


_GROK = SlideCover(
    asset_id=uuid4(), kind="screenshot", staged_path="g.webp", credit="x"
)


class TestOptions:
    @pytest.mark.asyncio
    async def test_library_then_offer_with_the_photo_current(self) -> None:
        a, b = _photo("a"), _photo("b")
        service, _ = _service(_Library((a, b)), _Offers(_GROK))
        found = await service.options(_project(hook_asset_id=a.id))
        assert found.current_asset_id == a.id
        assert [(o.asset_id, o.source, o.kind) for o in found.options] == [
            (a.id, "library", ""),
            (b.id, "library", ""),
            (_GROK.asset_id, "offer", "screenshot"),
        ]

    @pytest.mark.asyncio
    async def test_a_chosen_grok_cover_is_the_current_one(self) -> None:
        a = _photo("a")
        project = _project(hook_asset_id=a.id, slide_cover=_GROK)
        assert current_cover_asset(project) == _GROK.asset_id
        service, _ = _service(_Library((a,)))
        assert (await service.options(project)).current_asset_id == _GROK.asset_id

    @pytest.mark.asyncio
    async def test_no_owner_means_no_library(self) -> None:
        library = _Library((_photo("a"),))
        service, _ = _service(library)
        found = await service.options(_project(owner_id=None))
        assert found.options == ()
        assert library.asked == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", [None, "news_analysis"])
    async def test_radar_is_refused(self, mode: str | None) -> None:
        service, _ = _service(_Library(()))
        with pytest.raises(CoverPickError) as raised:
            await service.options(_project(content_mode=mode))
        assert raised.value.code == "cover_pick_not_pov"


class TestPick:
    @pytest.mark.asyncio
    async def test_library_photo_is_staged_then_bound(self) -> None:
        a, b = _photo("a"), _photo("b")
        library = _Library((a, b))
        service, switcher = _service(library, _Offers(_GROK))
        project = _project(hook_asset_id=a.id, content_mode="pov_news")
        await service.pick(
            CoverPickCommand(project=project, asset_id=b.id, expected_version=7)
        )
        assert library.staged == [b.id]
        assert switcher.commands == [
            SlideCoverSwitchCommand(
                project_id=str(project.id),
                expected_version=7,
                cover=None,
                hook_photo=HookPhotoChoice(asset_id=b.id, staged_path=b.relative_path),
            )
        ]

    @pytest.mark.asyncio
    async def test_offer_is_stored_as_the_cover(self) -> None:
        library = _Library((_photo("a"),))
        service, switcher = _service(library, _Offers(_GROK))
        project = _project()
        await service.pick(
            CoverPickCommand(
                project=project, asset_id=_GROK.asset_id, expected_version=2
            )
        )
        assert library.staged == []
        assert switcher.commands == [
            SlideCoverSwitchCommand(
                project_id=str(project.id), expected_version=2, cover=_GROK
            )
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("changes", "code"),
        [
            ({"content_mode": "news_analysis"}, "cover_pick_not_pov"),
            ({"status": CarouselStatus.EXPORTING}, "cover_pick_not_completed"),
            ({}, "cover_pick_asset_not_allowed"),
        ],
    )
    async def test_refused(self, changes: dict[str, object], code: str) -> None:
        library = _Library((_photo("a"),))
        service, switcher = _service(library)
        with pytest.raises(CoverPickError) as raised:
            await service.pick(
                CoverPickCommand(
                    project=_project(**changes), asset_id=uuid4(), expected_version=1
                )
            )
        assert raised.value.code == code
        assert (library.staged, switcher.commands) == ([], [])

    @pytest.mark.asyncio
    async def test_active_run_is_a_conflict(self) -> None:
        a = _photo("a")
        service, switcher = _service(_Library((a,)))
        with pytest.raises(CarouselConflictError) as raised:
            await service.pick(
                CoverPickCommand(
                    project=_project(phase_status="in_progress"),
                    asset_id=a.id,
                    expected_version=1,
                )
            )
        assert raised.value.conflict.code == "resume_already_in_progress"
        assert switcher.commands == []


class TestSwitchResultMapping:
    def test_conflict_is_a_typed_409(self) -> None:
        with pytest.raises(CarouselConflictError) as raised:
            _raise_unless_switched(SlideCoverSwitchResult(status="conflict"))
        assert raised.value.conflict.code == "version_conflict"

    def test_a_vanished_cover_is_422(self) -> None:
        with pytest.raises(HTTPException) as raised:
            _raise_unless_switched(SlideCoverSwitchResult(status="nothing_to_fix"))
        assert (raised.value.status_code, raised.value.detail) == (
            422,
            "cover_pick_asset_not_allowed",
        )

    def test_render_errors_raise_and_a_clean_switch_does_not(self) -> None:
        _raise_unless_switched(SlideCoverSwitchResult(status="fixed"))
        with pytest.raises(HTTPException) as raised:
            _raise_unless_switched(
                SlideCoverSwitchResult(status="fixed", render_errors=("boom",))
            )
        assert raised.value.status_code == 422


@dataclass
class _Repo:
    project: CarouselProject

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return self.project

    async def update_project(self, project: CarouselProject) -> CarouselProject:
        return project


@dataclass
class _Db:
    commits: int = 0

    async def commit(self) -> None:
        self.commits += 1


class _Unused:
    async def stage(self, project_id: str, cover: SlideCover) -> bool:
        raise AssertionError((project_id, cover))

    async def render(self, project_id: str) -> tuple[str, ...]:
        del project_id
        return ()


async def _unlocked(
    db: object, target: LockedWrite, write: Callable[[], Awaitable[None]]
) -> None:
    del db, target
    await write()


@pytest.mark.asyncio
async def test_switch_binds_the_hook_photo_and_clears_the_cover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Choosing a library photo replaces a GrokBot cover chosen on Telegram."""
    monkeypatch.setattr(slide_cover_switch, "write_locked", _unlocked)
    b = _photo("b")
    project = _project(hook_asset_id=uuid4(), slide_cover=_GROK)
    db = _Db()
    service = SlideCoverSwitchService(
        SlideCoverSwitchDeps(
            db=db, repo=_Repo(project), stager=_Unused(), renderer=_Unused()
        )
    )
    choice = HookPhotoChoice(asset_id=b.id, staged_path=b.relative_path)
    result = await service.switch(
        SlideCoverSwitchCommand(
            project_id=str(project.id),
            expected_version=3,
            cover=None,
            hook_photo=choice,
        )
    )
    assert result.status == "fixed"
    assert (project.hook_asset_id, project.hook_asset_staged_path) == (
        b.id,
        b.relative_path,
    )
    assert project.slide_cover is None
    assert db.commits == 1
