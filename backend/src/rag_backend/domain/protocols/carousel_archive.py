"""Port of the carousel auto-archive (Pedro's decision)."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class CarouselAutoArchiver(Protocol):
    """Archives carousels that sat idle too long."""

    async def archive_idle(self, db: AsyncSession, idle_days: int) -> int:
        """Archive every carousel idle for more than ``idle_days`` days.

        Skips published carousels, carousels whose phase is in progress and
        carousels already archived. Returns how many were archived; a second
        call in the same window archives nothing more.
        """
        ...


__all__ = ["CarouselAutoArchiver"]
