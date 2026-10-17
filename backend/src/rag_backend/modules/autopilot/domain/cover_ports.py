"""Ports of the GrokBot slide-1 cover (AE-0418, ADR-0024).

The SQL store keeps the autopilot's cover rows; the image store is the
editorial creator-asset seam (validation, WebP storage, staging); the
switcher re-renders a finished carousel with or without the cover.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState


@dataclass(frozen=True, kw_only=True)
class CoverImage:
    """The bytes to validate and store, their kind and the owning user."""

    owner_id: str
    content: bytes
    kind: str


@dataclass(frozen=True, kw_only=True)
class StoredImage:
    """The creator asset the image was stored as, and its final size."""

    creator_asset_id: UUID
    width: int
    height: int


@dataclass(frozen=True, kw_only=True)
class CoverClaim:
    """Mark a cover as used by the topic that was just stored."""

    asset_id: UUID
    topic_candidate_id: UUID


@dataclass(frozen=True, kw_only=True)
class ExpiredCoverQuery:
    """Unused covers created before ``before``, at most ``limit`` of them."""

    before: datetime
    limit: int


@dataclass(frozen=True, kw_only=True)
class CoverChoiceCommand:
    """Store the owner's slide-1 choice while the run is in ``expected``."""

    run_id: UUID
    expected: AutopilotRunState
    chosen: bool


class CoverSwitchStatus(StrEnum):
    """Outcome of one slide-1 switch on a finished carousel."""

    SWITCHED = "switched"
    CONFLICT = "conflict"
    MISSING = "missing"


@dataclass(frozen=True, kw_only=True)
class CoverSwitchCommand:
    """The carousel, the lock version read and the cover (None = default)."""

    project_id: str
    expected_version: int
    cover: SlideCover | None


class CoverAssetReader(Protocol):
    """Read the covers a batch or a run names."""

    async def covers_by_ids(self, ids: tuple[UUID, ...]) -> dict[UUID, CoverAsset]:
        """The stored covers among ``ids`` (unknown ids are absent)."""
        ...


class CoverIntakeStore(CoverAssetReader, Protocol):
    """What topic intake needs: read the named covers, claim the used one."""

    async def claim_cover(self, claim: CoverClaim) -> bool:
        """Set the first user; False when another topic took it first."""
        ...


class CoverAssetStore(CoverIntakeStore, Protocol):
    """Persist cover rows; the caller commits."""

    async def add_cover(self, cover: CoverAsset) -> None:
        """Insert a freshly uploaded cover."""
        ...

    async def expired_covers(self, query: ExpiredCoverQuery) -> tuple[CoverAsset, ...]:
        """Unused covers older than the cutoff, oldest first."""
        ...

    async def delete_covers(self, ids: tuple[UUID, ...]) -> None:
        """Delete the cover rows."""
        ...

    async def commit(self) -> None:
        """Commit the unit of work."""
        ...


class CoverImageStore(Protocol):
    """The creator-asset side: validate, store, read and delete images."""

    async def store_image(self, image: CoverImage) -> StoredImage:
        """Store a valid image; raises ``CoverAssetError`` with the code."""
        ...

    async def image_file(self, creator_asset_id: UUID) -> str | None:
        """The stored file of an image, or None when it is gone."""
        ...

    async def delete_images(self, creator_asset_ids: tuple[UUID, ...]) -> int:
        """Delete cover images and their files; returns how many."""
        ...


class CoverOffers(Protocol):
    """A run's GrokBot cover: the Telegram offer and, when chosen, slide 1."""

    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        """The offer, or None when the topic has no usable cover."""
        ...

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        """The project field when the owner chose the cover, else None."""
        ...


class CoverChoiceStore(Protocol):
    """Store the owner's slide-1 choice on the run (compare-and-set)."""

    async def set_cover_choice(self, command: CoverChoiceCommand) -> bool:
        """False when the run is not in ``expected`` any more."""
        ...


class CoverSwitcher(Protocol):
    """Re-render a finished carousel with the chosen slide 1."""

    async def switch(self, command: CoverSwitchCommand) -> CoverSwitchStatus:
        """Stage, store and re-render; a conflict writes nothing."""
        ...


__all__ = [
    "CoverAssetReader",
    "CoverAssetStore",
    "CoverChoiceCommand",
    "CoverChoiceStore",
    "CoverClaim",
    "CoverImage",
    "CoverImageStore",
    "CoverIntakeStore",
    "CoverOffers",
    "CoverSwitchCommand",
    "CoverSwitchStatus",
    "CoverSwitcher",
    "ExpiredCoverQuery",
    "StoredImage",
]
