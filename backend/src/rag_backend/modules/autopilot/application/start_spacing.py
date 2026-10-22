"""Hold a queued run until the previous generation start is old enough."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import structlog

from rag_backend.modules.autopilot.domain.models import AutopilotRun
from rag_backend.modules.autopilot.domain.ports import Clock
from rag_backend.modules.autopilot.domain.start_spacing import (
    NO_WAIT,
    StartHistory,
    start_wait,
)
from rag_backend.modules.autopilot.start_spacing_constants import LOG_START_SPACED

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class StartSpacing:
    """At least ``minimum`` between two generation starts.

    The check reads the latest start and then creates the project without a lock:
    it relies on the single in-process worker loop stepping one run per tick, so
    two starts never race. A second runner process would need a lock here.
    """

    starts: StartHistory
    clock: Clock
    minimum: timedelta

    async def holds(self, run: AutopilotRun) -> bool:
        """True (and logged) while ``run`` must stay queued."""
        if self.minimum <= NO_WAIT:
            return False
        latest = await self.starts.latest_start(run.run_id)
        wait = start_wait(latest, self.clock.now(), self.minimum)
        if wait <= NO_WAIT:
            return False
        logger.info(
            LOG_START_SPACED,
            run_id=str(run.run_id),
            wait_seconds=int(wait.total_seconds()),
        )
        return True
