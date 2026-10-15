"""System ``BridgeClock`` (AE-0393)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime


class SystemClock:
    """Wall-clock UTC time and ``asyncio.sleep``."""

    @staticmethod
    def now() -> datetime:
        """Current UTC time."""
        return datetime.now(UTC)

    @staticmethod
    async def sleep(seconds: float) -> None:
        """Sleep without blocking the event loop."""
        await asyncio.sleep(seconds)
