"""Ports of the repost source video upload."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.repost_source import (
    RepostSource,
    VideoProbe,
)


class RepostSourceStore(Protocol):
    """Persistence for uploaded source videos."""

    async def insert(self, source: RepostSource) -> None:
        """Store a new upload."""
        ...

    async def get(self, asset_id: UUID) -> RepostSource | None:
        """One upload."""
        ...

    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        """Mark an unused upload as the draft's; False when it is taken."""
        ...

    async def unused_before(self, before: datetime) -> tuple[RepostSource, ...]:
        """Unused uploads created before ``before``."""
        ...

    async def delete(self, asset_id: UUID) -> None:
        """Drop an upload's row."""
        ...

    async def commit(self) -> None:
        """Commit the unit of work."""
        ...


class VideoProber(Protocol):
    """Reads a local video's codec, size and duration."""

    async def probe(self, path: Path) -> VideoProbe | None:
        """None when the file is not a readable video."""
        ...


class SourceFolder(Protocol):
    """Where accepted uploads are kept."""

    def promote(self, part: Path, asset_id: UUID) -> str:
        """Move a checked upload to its final name; return the file name."""
        ...

    def remove(self, source: RepostSource) -> None:
        """Delete an upload's file if it is still there."""
        ...


__all__ = ["RepostSourceStore", "SourceFolder", "VideoProber"]
