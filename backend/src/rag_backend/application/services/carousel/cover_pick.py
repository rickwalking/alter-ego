"""The publish-step slide-1 cover picker of a Ponto de Vista carousel.

The owner of a finished ``pov`` / ``pov_news`` carousel picks slide 1's image
among their library photos (role ``hook``) and the autopilot run's GrokBot
cover offer:

- a library photo is staged, bound as the slide-1 photo (``hook_asset_id``)
  and any GrokBot cover is cleared, so the default POV slide 1 shows it;
- the GrokBot offer is stored as ``slide_cover`` (the Telegram semantics).

Both write through ``SlideCoverSwitchService``: lock-version CAS under the
project lock, then the republish (slides + PDFs, hero images reused).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.application.services.carousel.slide_cover_switch import (
    HookPhotoChoice,
    SlideCoverSwitchCommand,
    SlideCoverSwitchResult,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_cover_pick import (
    COVER_SOURCE_LIBRARY,
    COVER_SOURCE_OFFER,
    ERR_COVER_PICK_ASSET_NOT_ALLOWED,
    ERR_COVER_PICK_NOT_COMPLETED,
    ERR_COVER_PICK_NOT_POV,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.content_mode import is_pov_family
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.slide_cover import SlideCover


class CoverPickError(ValueError):
    """A refused pick; ``code`` is the public 422 detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class CoverLibrary(Protocol):
    """The owner's slide-1 photos and their staging."""

    async def photos(self, owner_id: str) -> tuple[CarouselCreatorAsset, ...]:
        """Library photos (role ``hook``) whose stored file exists."""
        ...

    async def stage(
        self, project: CarouselProject, asset: CarouselCreatorAsset
    ) -> None:
        """Copy the photo where the project's slides render."""
        ...


class CoverOfferSource(Protocol):
    """The GrokBot cover offered to the carousel's autopilot run, if any."""

    async def offer(self, project_id: str) -> SlideCover | None: ...


class CoverSwitcher(Protocol):
    """Store the choice under the lock-version CAS and re-render."""

    async def switch(
        self, command: SlideCoverSwitchCommand
    ) -> SlideCoverSwitchResult: ...


@dataclass(frozen=True, kw_only=True)
class CoverPickDeps:
    """Where the options come from and how a pick is applied."""

    library: CoverLibrary
    offers: CoverOfferSource
    switcher: CoverSwitcher


@dataclass(frozen=True, kw_only=True)
class CoverOption:
    """One image slide 1 may show."""

    asset_id: UUID
    source: str
    kind: str = ""


@dataclass(frozen=True, kw_only=True)
class CoverOptions:
    """What slide 1 shows now and what it may show instead."""

    current_asset_id: UUID | None
    options: tuple[CoverOption, ...]


@dataclass(frozen=True, kw_only=True)
class CoverPickCommand:
    """The project, the chosen asset and the lock version the caller read."""

    project: CarouselProject
    asset_id: UUID
    expected_version: int


@dataclass(frozen=True, kw_only=True)
class _Candidates:
    library: tuple[CarouselCreatorAsset, ...]
    offer: SlideCover | None


def current_cover_asset(project: CarouselProject) -> UUID | None:
    """The asset slide 1 shows: the GrokBot cover when chosen, else the photo."""
    if project.slide_cover is not None:
        return project.slide_cover.asset_id
    return project.hook_asset_id


def _assert_pov(project: CarouselProject) -> None:
    if not is_pov_family(project.content_mode):
        raise CoverPickError(ERR_COVER_PICK_NOT_POV)


def _assert_switchable(project: CarouselProject) -> None:
    """Completed, with no workflow run in flight (the republish invariant)."""
    _assert_pov(project)
    if project.status != CarouselStatus.COMPLETED:
        raise CoverPickError(ERR_COVER_PICK_NOT_COMPLETED)
    if project.phase_status == PHASE_STATUS_IN_PROGRESS:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )


class CoverPickService:
    """List the slide-1 options of a POV carousel and apply the owner's pick."""

    def __init__(self, deps: CoverPickDeps) -> None:
        self._deps = deps

    async def options(self, project: CarouselProject) -> CoverOptions:
        """The library photos, then the GrokBot offer; 422 for non-POV."""
        _assert_pov(project)
        found = await self._candidates(project)
        library = tuple(
            CoverOption(asset_id=asset.id, source=COVER_SOURCE_LIBRARY)
            for asset in found.library
        )
        offer = found.offer
        offered = (
            (
                CoverOption(
                    asset_id=offer.asset_id, source=COVER_SOURCE_OFFER, kind=offer.kind
                ),
            )
            if offer is not None
            else ()
        )
        return CoverOptions(
            current_asset_id=current_cover_asset(project), options=(*library, *offered)
        )

    async def pick(self, command: CoverPickCommand) -> SlideCoverSwitchResult:
        """Stage, store and re-render; raises ``CoverPickError`` when refused."""
        project = command.project
        _assert_switchable(project)
        found = await self._candidates(project)
        offer = found.offer
        if offer is not None and offer.asset_id == command.asset_id:
            return await self._deps.switcher.switch(_switch_command(command, offer))
        photo = next((a for a in found.library if a.id == command.asset_id), None)
        if photo is None:
            raise CoverPickError(ERR_COVER_PICK_ASSET_NOT_ALLOWED)
        await self._deps.library.stage(project, photo)
        choice = HookPhotoChoice(asset_id=photo.id, staged_path=photo.relative_path)
        return await self._deps.switcher.switch(_switch_command(command, None, choice))

    async def _candidates(self, project: CarouselProject) -> _Candidates:
        owner_id = project.owner_id or ""
        library = await self._deps.library.photos(owner_id) if owner_id else ()
        offer = await self._deps.offers.offer(str(project.id))
        return _Candidates(library=library, offer=offer)


def _switch_command(
    command: CoverPickCommand,
    cover: SlideCover | None,
    hook_photo: HookPhotoChoice | None = None,
) -> SlideCoverSwitchCommand:
    return SlideCoverSwitchCommand(
        project_id=str(command.project.id),
        expected_version=command.expected_version,
        cover=cover,
        hook_photo=hook_photo,
    )


__all__ = [
    "CoverLibrary",
    "CoverOfferSource",
    "CoverOption",
    "CoverOptions",
    "CoverPickCommand",
    "CoverPickDeps",
    "CoverPickError",
    "CoverPickService",
    "CoverSwitcher",
    "current_cover_asset",
]
