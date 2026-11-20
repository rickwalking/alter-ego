"""Ports of the Reels list and the repost flow (ADR-0031)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.reels import LastRepost, ReelFacts, ReelMedia
from rag_backend.modules.autopilot.domain.repost import Repost, RepostListQuery


@dataclass(frozen=True, kw_only=True)
class StatusChange:
    """The row after a transition, and the status it must still be in."""

    expected: str
    repost: Repost


class RepostStore(Protocol):
    """Persistence for repost drafts."""

    async def lock(self) -> None:
        """Serialise draft creation for the rest of the transaction."""
        ...

    async def by_key(self, key: str) -> Repost | None:
        """The draft for an idempotency key, if any."""
        ...

    async def get(self, repost_id: UUID) -> Repost | None:
        """One draft."""
        ...

    async def live_since(self, media_id: str, since: datetime) -> bool:
        """True when a live repost of the Reel was created since ``since``."""
        ...

    async def drafts_since(self, since: datetime) -> int:
        """Drafts created since ``since`` that count toward the weekly cap."""
        ...

    async def insert(self, repost: Repost) -> None:
        """Store a new draft."""
        ...

    async def save(self, change: StatusChange) -> bool:
        """Replace the row while it is still ``expected``; False otherwise."""
        ...

    async def list_reposts(self, query: RepostListQuery) -> list[Repost]:
        """Newest first."""
        ...

    async def due(self, now: datetime) -> list[Repost]:
        """Drafts the worker should act on now, oldest first."""
        ...

    async def caption_editing(self, since: datetime) -> Repost | None:
        """The pending draft waiting for a caption typed after ``since``."""
        ...

    async def latest_for(self, media_ids: Sequence[str]) -> dict[str, LastRepost]:
        """The newest repost per original Reel."""
        ...

    async def hidden_media(self, since: datetime | None) -> frozenset[str]:
        """Every repost's new media, plus Reels with a live repost since ``since``."""
        ...

    async def commit(self) -> None:
        """Commit the session."""
        ...


class ReelGateway(Protocol):
    """Graph reads of the account's Reels."""

    async def list_reels(self, since: datetime) -> list[ReelMedia]:
        """Newest first, published at or after ``since``."""
        ...

    async def reel(self, media_id: str) -> ReelMedia | None:
        """One of the account's media with fresh URLs, or None."""
        ...

    async def collaborators(self, media_id: str) -> tuple[str, ...]:
        """Collaborator usernames of one media."""
        ...


class ReelProbe(Protocol):
    """Reads a video's duration."""

    async def duration(self, url: str) -> float | None:
        """Seconds, or None when the probe is unavailable or fails."""
        ...


class ReelFactsStore(Protocol):
    """Cache of durations and collaborators."""

    async def facts(self, media_ids: Sequence[str]) -> dict[str, ReelFacts]:
        """Known facts per media id."""
        ...

    async def save_facts(self, facts: ReelFacts) -> None:
        """Insert or replace one row."""
        ...


class RepostCovers(Protocol):
    """Reel cover rows."""

    async def covers_by_ids(self, ids: tuple[UUID, ...]) -> dict[UUID, CoverAsset]:
        """The stored covers among ``ids``."""
        ...

    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        """Mark an unused Reel cover as the repost's."""
        ...


__all__ = [
    "ReelFactsStore",
    "ReelGateway",
    "ReelProbe",
    "RepostCovers",
    "RepostStore",
    "StatusChange",
]
