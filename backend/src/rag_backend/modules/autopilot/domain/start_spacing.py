"""When the next queued autopilot run may start."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

NO_WAIT = timedelta(0)


class StartHistory(Protocol):
    """Reads when the latest autopilot generation started."""

    async def latest_start(self, exclude_run: UUID) -> datetime | None:
        """The newest start of any run other than ``exclude_run``, or None."""
        ...


def start_wait(latest: datetime | None, now: datetime, minimum: timedelta) -> timedelta:
    """How long a queued run still waits; ``NO_WAIT`` when it may start now."""
    if latest is None or minimum <= NO_WAIT:
        return NO_WAIT
    return max(NO_WAIT, latest + minimum - now)
