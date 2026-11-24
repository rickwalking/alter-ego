"""In-memory fakes for the repost source video upload."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.domain.repost_source import (
    RepostSource,
    VideoProbe,
)
from tests.unit.modules.autopilot.repost_fakes import NOW

HD = VideoProbe(codec="h264", width=1080, height=1920, duration_s=86.0)


def source(**changes: object) -> RepostSource:
    """A fresh unused 1080x1920 H.264 upload of 86 s."""
    asset_id = uuid4()
    base = RepostSource(
        id=asset_id,
        file_name=f"{asset_id}.mp4",
        size_bytes=59_000_000,
        probe=HD,
        created_at=NOW,
    )
    return replace(base, **changes)


@dataclass
class MemorySources:
    """``RepostSourceStore`` over a dict."""

    rows: dict[UUID, RepostSource] = field(default_factory=dict)
    commits: int = 0
    deleted: list[UUID] = field(default_factory=list)

    async def insert(self, item: RepostSource) -> None:
        self.rows[item.id] = item

    async def get(self, asset_id: UUID) -> RepostSource | None:
        return self.rows.get(asset_id)

    async def claim_for_repost(self, asset_id: UUID, repost_id: UUID) -> bool:
        found = self.rows.get(asset_id)
        if found is None or found.repost_id is not None:
            return False
        self.rows[asset_id] = replace(found, repost_id=repost_id)
        return True

    async def unused_before(self, before: datetime) -> tuple[RepostSource, ...]:
        return tuple(
            row
            for row in self.rows.values()
            if row.repost_id is None and row.created_at < before
        )

    async def delete(self, asset_id: UUID) -> None:
        self.deleted.append(asset_id)
        self.rows.pop(asset_id, None)

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class FakeProber:
    """``VideoProber`` returning a fixed probe."""

    result: VideoProbe | None = HD

    async def probe(self, path: Path) -> VideoProbe | None:
        del path
        return self.result


__all__ = ["HD", "FakeProber", "MemorySources", "source"]
