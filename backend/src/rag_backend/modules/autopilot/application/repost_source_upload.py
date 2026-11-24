"""Accept an uploaded source video for a later repost draft.

The route streams the file to a ``.part`` file under the size cap. This use
case probes it, keeps it only when it is an H.264 portrait video of 3-180 s,
and stores its row. Uploads no draft used within 24 h are swept.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import structlog

from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.repost_source import (
    RepostSource,
    SourceError,
    check_video,
)
from rag_backend.modules.autopilot.domain.repost_source_ports import (
    RepostSourceStore,
    SourceFolder,
    VideoProber,
)
from rag_backend.modules.autopilot.repost_source_constants import (
    LOG_REPOST_SOURCE,
    LOG_SOURCE_REFUSED,
    LOG_SOURCE_STORED,
    LOG_SOURCE_SWEPT,
    SOURCE_TTL_HOURS,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class SourceUploadDeps:
    """The store, ffprobe, the folder and the clock."""

    store: RepostSourceStore
    prober: VideoProber
    folder: SourceFolder
    clock: Clock


@dataclass(frozen=True, kw_only=True)
class SourceUpload:
    """A file the route already wrote under the size cap."""

    asset_id: UUID
    part: Path
    size_bytes: int


class RepostSourceUploads:
    """``POST /api/autopilot/assets/video``."""

    def __init__(self, deps: SourceUploadDeps) -> None:
        self._deps = deps

    async def accept(self, upload: SourceUpload) -> RepostSource:
        """Check and keep the upload; ``SourceError`` when it is refused."""
        try:
            probe = check_video(await self._deps.prober.probe(upload.part))
        except SourceError as exc:
            upload.part.unlink(missing_ok=True)
            logger.info(LOG_REPOST_SOURCE, outcome=LOG_SOURCE_REFUSED, code=exc.code)
            raise
        now = self._deps.clock.now()
        source = RepostSource(
            id=upload.asset_id,
            file_name=self._deps.folder.promote(upload.part, upload.asset_id),
            size_bytes=upload.size_bytes,
            probe=probe,
            created_at=now,
        )
        await self._deps.store.insert(source)
        await self._sweep(source)
        await self._deps.store.commit()
        logger.info(
            LOG_REPOST_SOURCE,
            outcome=LOG_SOURCE_STORED,
            asset_id=str(source.id),
            size_bytes=source.size_bytes,
        )
        return source

    async def _sweep(self, fresh: RepostSource) -> None:
        before = fresh.created_at - timedelta(hours=SOURCE_TTL_HOURS)
        stale = await self._deps.store.unused_before(before)
        for source in stale:
            self._deps.folder.remove(source)
            await self._deps.store.delete(source.id)
        if stale:
            logger.info(LOG_REPOST_SOURCE, outcome=LOG_SOURCE_SWEPT, count=len(stale))


__all__ = ["RepostSourceUploads", "SourceUpload", "SourceUploadDeps"]
