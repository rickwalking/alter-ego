"""Autopilot auto-cover: the editorial helper through the real service path.

Gherkin: tests/features/autopilot_cover_autostart_ae0581.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel import cover_generation_tasks
from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationError,
    CoverGenerationRefusedError,
    StartCoverGeneration,
)
from rag_backend.domain.constants.carousel_cover_pick import ERR_COVER_PICK_NOT_POV
from rag_backend.domain.constants.cover_generation import (
    COVER_GENERATION_MAX_PHOTOS,
    ERR_COVER_GENERATION_MONTHLY_CAP,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.modules.editorial.infrastructure import (
    carousel_cover_autoselect,
    carousel_cover_autostart,
    cover_generations,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autostart import (
    schedule_autopilot_cover,
)
from rag_backend.modules.image_bridge import ImageBridgeConfigError

_PROJECT = "22222222-2222-2222-2222-222222222222"
_OWNER = "owner-1"
_PHOTOS = tuple(uuid4() for _ in range(4))


def _project(
    owner: str | None = _OWNER, topic: str = "Agentes em produção"
) -> CarouselProject:
    project = CarouselProject(topic=topic, audience="Devs", niche="IA")
    project.owner_id = owner
    project.content_mode = "pov"
    return project


@dataclass
class _Acl:
    project: CarouselProject | None

    async def load_project(self, project_id: str) -> CarouselProject | None:
        return self.project


@dataclass(frozen=True)
class _Asset:
    id: UUID


@dataclass
class _Library:
    ids: tuple[UUID, ...]
    calls: int = 0

    async def photos(self, owner_id: str) -> tuple[_Asset, ...]:
        self.calls += 1
        return tuple(_Asset(asset_id) for asset_id in self.ids)


@dataclass
class _Service:
    started: list[StartCoverGeneration] = field(default_factory=list)
    error: Exception | None = None

    async def start(self, command: StartCoverGeneration) -> object:
        if self.error is not None:
            raise self.error
        self.started.append(command)
        return _Run(_Generation(uuid4()))


@dataclass(frozen=True)
class _Generation:
    id: UUID


@dataclass(frozen=True)
class _Run:
    generation: _Generation


def _helper(
    monkeypatch: pytest.MonkeyPatch,
    *,
    project: CarouselProject | None,
    photos: _Library,
    service: _Service,
    wiring_error: Exception | None = None,
) -> list[str]:
    """Install fakes on the editorial helper; returns the scheduled ids."""
    scheduled: list[str] = []
    monkeypatch.setattr(
        carousel_cover_autostart, "CarouselAutomationAcl", lambda _s: _Acl(project)
    )
    monkeypatch.setattr(
        carousel_cover_autostart, "EditorialCoverLibrary", lambda _s: photos
    )

    class _Generations:
        rows: tuple[object, ...] = ()

        async def for_project(self, project_id: str) -> tuple[object, ...]:
            return self.rows

    monkeypatch.setattr(
        cover_generations, "SqlCoverGenerationRepository", lambda _s: _Generations()
    )

    def _wiring(_renderer: object) -> object:
        if wiring_error is not None:
            raise wiring_error
        return object()

    monkeypatch.setattr(carousel_cover_autostart, "cover_run_wiring", _wiring)
    monkeypatch.setattr(
        carousel_cover_autostart, "cover_generation_service", lambda _s: service
    )
    monkeypatch.setattr(
        carousel_cover_autoselect, "cover_generation_task", lambda _w, run: run
    )
    monkeypatch.setattr(
        cover_generation_tasks,
        "schedule_cover_generation",
        lambda run, generation_id: scheduled.append(generation_id),
    )
    return scheduled


@pytest.mark.unit
class TestScheduleAutopilotCover:
    # Scenario: A fresh autopilot carousel gets one cover job
    @pytest.mark.asyncio
    async def test_one_job_with_capped_photos(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service()
        photos = _Library(_PHOTOS)
        scheduled = _helper(
            monkeypatch, project=_project(), photos=photos, service=service
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert outcome.scheduled
        assert len(service.started) == 1
        command = service.started[0]
        assert command.confirmed
        assert command.user_id == _OWNER
        assert command.prompt == "Agentes em produção"
        assert command.photo_ids == _PHOTOS[:COVER_GENERATION_MAX_PHOTOS]
        assert scheduled == [outcome.generation_id]

    # Scenario: The owner picked fewer than three photos
    @pytest.mark.asyncio
    async def test_fewer_photos_all_go(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        two = (uuid4(), uuid4())
        service = _Service()
        _helper(monkeypatch, project=_project(), photos=_Library(two), service=service)

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert outcome.scheduled
        assert service.started[0].photo_ids == two

    # Scenario: A cap refusal skips the job
    @pytest.mark.asyncio
    async def test_cap_refusal_skips(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service(
            error=CoverGenerationRefusedError(ERR_COVER_GENERATION_MONTHLY_CAP)
        )
        scheduled = _helper(
            monkeypatch, project=_project(), photos=_Library(_PHOTOS), service=service
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason == f"refused:{ERR_COVER_GENERATION_MONTHLY_CAP}"
        assert scheduled == []

    # Scenario: Without library photos the step skips
    @pytest.mark.asyncio
    async def test_no_photos_skips(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service()
        _helper(
            monkeypatch,
            project=_project(),
            photos=_Library(()),
            service=service,
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason == "no_photos"
        assert service.started == []

    # Scenario: A re-driven run does not enqueue a second cover
    @pytest.mark.asyncio
    async def test_existing_generation_dedups(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service()
        photos = _Library(_PHOTOS)
        _helper(monkeypatch, project=_project(), photos=photos, service=service)

        class _Generations:
            async def for_project(self, project_id: str) -> tuple[object, ...]:
                return (object(),)

        monkeypatch.setattr(
            cover_generations,
            "SqlCoverGenerationRepository",
            lambda _s: _Generations(),
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason == "already_exists"
        assert service.started == []
        assert photos.calls == 0

    @pytest.mark.asyncio
    async def test_no_project_or_no_owner_skips(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        photos = _Library(_PHOTOS)
        _helper(monkeypatch, project=None, photos=photos, service=_Service())

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason == "no_project"
        assert photos.calls == 0

    # Scenario: An unconfigured bridge skips the job
    @pytest.mark.asyncio
    async def test_bridge_unavailable_skips(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service()
        scheduled = _helper(
            monkeypatch,
            project=_project(),
            photos=_Library(_PHOTOS),
            service=service,
            wiring_error=ImageBridgeConfigError("off"),
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason == "bridge_unavailable"
        assert scheduled == []

    @pytest.mark.asyncio
    async def test_non_pov_carousel_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        service = _Service(error=CoverGenerationError(ERR_COVER_PICK_NOT_POV))
        _helper(
            monkeypatch, project=_project(), photos=_Library(_PHOTOS), service=service
        )

        outcome = await schedule_autopilot_cover(db_session, _PROJECT)

        assert not outcome.scheduled
        assert outcome.reason.startswith("refused:")
