"""Delete GrokBot covers nobody used within 6 hours (AE-0418, ADR-0024).

Runs on the Telegram notify tick (every worker cycle). Each pass deletes at
most ``COVER_SWEEP_LIMIT`` covers, oldest first: the cover rows, then their
creator-asset images and files, in one commit.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.cover_constants import (
    COVER_SWEEP_LIMIT,
    LOG_COVER,
    LOG_COVER_SWEPT,
)
from rag_backend.modules.autopilot.domain.cover import expiry_cutoff
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverAssetStore,
    CoverImageStore,
    ExpiredCoverQuery,
)
from rag_backend.modules.autopilot.domain.ports import Clock

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class CoverSweepDependencies:
    """The cover rows, the image store and the clock."""

    covers: CoverAssetStore
    images: CoverImageStore
    clock: Clock


class CoverSweepService:
    """One bounded sweep per tick."""

    def __init__(self, deps: CoverSweepDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Delete the expired, unused covers. Returns how many rows went."""
        query = ExpiredCoverQuery(
            before=expiry_cutoff(self._deps.clock.now()), limit=COVER_SWEEP_LIMIT
        )
        expired = await self._deps.covers.expired_covers(query)
        if not expired:
            return 0
        await self._deps.covers.delete_covers(tuple(c.asset_id for c in expired))
        await self._deps.images.delete_images(
            tuple(c.creator_asset_id for c in expired)
        )
        await self._deps.covers.commit()
        logger.info(LOG_COVER, outcome=LOG_COVER_SWEPT, count=len(expired))
        return len(expired)


__all__ = ["CoverSweepDependencies", "CoverSweepService"]
