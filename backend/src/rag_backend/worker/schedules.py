"""Daily jobs on PgQueuer's scheduler (cron in UTC; PgQueuer runs each once a day).

* 11:05 UTC (08:05 São Paulo): promote waiting backlog themes into the day's free
  slots, so they start even on a day the scout sends no batch. Registered only
  while the worker drives autopilot runs.

A failed job is logged; the next day's run tries again.
"""

from __future__ import annotations

import structlog
from pgqueuer import PgQueuer
from pgqueuer.models import Schedule

from rag_backend.modules.autopilot.queue_bridge import AutopilotQueueBridge
from rag_backend.modules.autopilot.queue_constants import (
    BACKLOG_PROMOTION_CRON_UTC,
    BACKLOG_PROMOTION_ENTRYPOINT,
    LOG_BACKLOG_PROMOTED,
    LOG_BACKLOG_PROMOTION_FAILED,
)

logger = structlog.get_logger()


async def run_backlog_promotion(bridge: AutopilotQueueBridge) -> int | None:
    """Promote the waiting themes; None when the promotion failed."""
    try:
        promoted = await bridge.promote_backlog()
    except Exception:
        logger.exception(LOG_BACKLOG_PROMOTION_FAILED, exc_info=True)
        return None
    logger.info(LOG_BACKLOG_PROMOTED, promoted=promoted)
    return promoted


def register_backlog_promotion(pgq: PgQueuer, bridge: AutopilotQueueBridge) -> None:
    """Put the morning backlog promotion on PgQueuer's scheduler."""

    async def promote(schedule: Schedule) -> None:
        del schedule
        await run_backlog_promotion(bridge)

    pgq.schedule(BACKLOG_PROMOTION_ENTRYPOINT, BACKLOG_PROMOTION_CRON_UTC)(promote)


__all__ = ["register_backlog_promotion", "run_backlog_promotion"]
