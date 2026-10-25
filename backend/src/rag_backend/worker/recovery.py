"""The daily recovery scan on PgQueuer's scheduler: 07:00 UTC (04:00 São Paulo).

PgQueuer keeps the schedule in its own table, so with several workers (or a
restart around 07:00) the scan runs once a day. A failed scan is logged; the next
day's scan tries again.
"""

from __future__ import annotations

from collections.abc import Callable

import structlog
from pgqueuer import PgQueuer
from pgqueuer.models import Schedule

from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    summary_text,
)
from rag_backend.modules.generation_queue.constants import (
    LOG_SCAN_DONE,
    LOG_SCAN_FAILED,
    SCAN_CRON_UTC,
    SCAN_ENTRYPOINT,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport

logger = structlog.get_logger()

AlertSender = Callable[[str], None]


async def run_daily_scan(
    scan: DailyRecoveryScan, alert: AlertSender
) -> ScanReport | None:
    """Run the scan and send Pedro its summary; None when the scan failed."""
    try:
        report = await scan.run_once()
    except Exception:
        logger.exception(LOG_SCAN_FAILED, exc_info=True)
        return None
    alert(summary_text(report))
    logger.info(
        LOG_SCAN_DONE,
        recovered=report.recovered,
        still_dead=report.still_dead,
        queued=report.queued,
        purged_runs=report.purged_runs,
        purged_logs=report.purged_logs,
    )
    return report


def register_daily_scan(
    pgq: PgQueuer, scan: DailyRecoveryScan, alert: AlertSender
) -> None:
    """Put the scan on PgQueuer's scheduler."""

    async def daily_scan(schedule: Schedule) -> None:
        del schedule
        await run_daily_scan(scan, alert)

    pgq.schedule(SCAN_ENTRYPOINT, SCAN_CRON_UTC)(daily_scan)


__all__ = ["register_daily_scan", "run_daily_scan"]
