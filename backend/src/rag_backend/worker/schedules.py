"""The 11:05 UTC backlog schedule enqueues the shared full control job.

The maintenance executor runs ``run_backlog_promotion`` under the full-pass lock,
so cron never promotes independently of manual maintenance.
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
from rag_backend.modules.generation_queue.domain.maintenance import (
    FullMaintenanceControl,
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


def register_backlog_promotion(pgq: PgQueuer, control: FullMaintenanceControl) -> None:
    """Enqueue the shared full control job on the morning schedule."""

    async def promote(schedule: Schedule) -> None:
        del schedule
        await control.request_full()

    pgq.schedule(BACKLOG_PROMOTION_ENTRYPOINT, BACKLOG_PROMOTION_CRON_UTC)(promote)


__all__ = ["register_backlog_promotion", "run_backlog_promotion"]
