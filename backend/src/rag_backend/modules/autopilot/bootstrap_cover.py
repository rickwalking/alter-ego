"""Worker wiring for the GrokBot slide-1 cover (AE-0418, ADR-0024)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.application.cover_sweep import (
    CoverSweepDependencies,
    CoverSweepService,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore


def cover_sweep(db: AsyncSession) -> CoverSweepService:
    """The sweep of unused covers on the tick's session."""
    return CoverSweepService(
        CoverSweepDependencies(
            covers=SqlCoverAssetStore(db),
            images=EditorialCoverImages(db),
            clock=SystemClock(),
        )
    )


__all__ = ["cover_sweep"]
