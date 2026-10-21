"""Slide-1 cover switch service with fakes (ADR-0024).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: The Radar IA review offers the cover and swaps slide 1
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel import slide_cover_switch
from rag_backend.application.services.carousel.owner_autofix_lock import LockedWrite
from rag_backend.application.services.carousel.slide_cover_switch import (
    SlideCoverSwitchCommand,
    SlideCoverSwitchDeps,
    SlideCoverSwitchService,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.slide_cover import SlideCover


@dataclass
class _Repo:
    project: CarouselProject | None
    updates: list[CarouselProject] = field(default_factory=list)

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return self.project

    async def update_project(self, project: CarouselProject) -> CarouselProject:
        self.updates.append(project)
        return project


@dataclass
class _Db:
    commits: int = 0

    async def commit(self) -> None:
        self.commits += 1


class _Stager:
    async def stage(self, project_id: str, cover: SlideCover) -> bool:
        del project_id, cover
        return True


class _Renderer:
    async def render(self, project_id: str) -> tuple[str, ...]:
        return (f"render_error:{project_id}",)


async def _unlocked(
    db: object, target: LockedWrite, write: Callable[[], Awaitable[None]]
) -> None:
    del db, target
    await write()


@pytest.mark.asyncio
async def test_unknown_project_writes_nothing_and_render_errors_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slide_cover_switch, "write_locked", _unlocked)
    repo, db = _Repo(project=None), _Db()
    service = SlideCoverSwitchService(
        SlideCoverSwitchDeps(db=db, repo=repo, stager=_Stager(), renderer=_Renderer())
    )
    cover = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="a.webp")
    result = await service.switch(
        SlideCoverSwitchCommand(
            project_id=str(uuid4()), expected_version=1, cover=cover
        )
    )
    assert result.status == "fixed"
    assert result.render_errors[0].startswith("render_error:")
    assert repo.updates == []
    assert db.commits == 0
