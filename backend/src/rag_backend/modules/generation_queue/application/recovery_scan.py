"""The daily recovery scan: one pass at 04:00 São Paulo time (PgQueuer schedule).

1. Retry once each autopilot drive the queue parked in the last 7 days for a
   transient-class reason: marking and reviving commit atomically, and one failed
   item is logged and reported without stopping the others.
2. Resume the autopilot runs escalated as stale in the last 72 hours.
3. Purge succeeded runs and PgQueuer log rows older than 30 days.
4. Count what is still dead and what is queued, list the parked dashboard projects.
The caller sends Pedro the summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from rag_backend.modules.generation_queue.constants import (
    FAILURE_REASON_MAX_CHARS,
    LOG_SCAN_ITEM_FAILED,
    SCAN_PURGE_DAYS,
    SCAN_RECOVERY_DAYS,
    SCAN_STALE_HOURS,
    SUMMARY_FAILURE_ITEM,
    SUMMARY_FAILURES,
    SUMMARY_INTERACTIVE,
    SUMMARY_SCAN,
    SUMMARY_TITLE_MAX_CHARS,
    SUMMARY_TITLES_MAX,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
from rag_backend.modules.generation_queue.domain.recovery import (
    ParkedAutopilot,
    ParkedDrive,
    RecoveryFailure,
    RecoveryStore,
    ScanReport,
)

logger = structlog.get_logger()

_TITLE_SEPARATOR = "; "
_ELLIPSIS = "…"
_REASON_SEPARATOR = ": "


@dataclass(frozen=True, kw_only=True)
class DailyScanDependencies:
    """The queue store, the autopilot bridge and the clock."""

    store: RecoveryStore
    autopilot: ParkedAutopilot
    clock: Clock


class DailyRecoveryScan:
    """Recover, purge and count, once."""

    def __init__(self, deps: DailyScanDependencies) -> None:
        self._deps = deps

    async def run_once(self) -> ScanReport:
        """One scan; the report the summary is written from."""
        now = self._deps.clock.now()
        window = now - timedelta(days=SCAN_RECOVERY_DAYS)
        recovered, failures = await self._retry_dead_letters(window)
        recovered += await self._deps.autopilot.revive_stale(
            now - timedelta(hours=SCAN_STALE_HOURS)
        )
        purged_runs, purged_logs = await self._deps.store.purge(
            now - timedelta(days=SCAN_PURGE_DAYS)
        )
        return ScanReport(
            recovered=recovered,
            still_dead=await self._deps.store.dead_letters(window),
            queued=await self._deps.store.active(),
            purged_runs=purged_runs,
            purged_logs=purged_logs,
            interactive=tuple(await self._deps.store.interactive_orphans()),
            failures=failures,
        )

    async def _retry_dead_letters(
        self, since: datetime
    ) -> tuple[int, tuple[RecoveryFailure, ...]]:
        recovered = 0
        failures: list[RecoveryFailure] = []
        for drive in await self._deps.store.recoverable(since):
            try:
                revived = await self._deps.autopilot.revive_dead_letter(drive)
            except Exception as exc:
                failures.append(_item_failure(drive, exc))
                continue
            recovered += int(revived)
        return recovered, tuple(failures)


def _item_failure(drive: ParkedDrive, exc: Exception) -> RecoveryFailure:
    logger.warning(
        LOG_SCAN_ITEM_FAILED,
        generation_run_id=str(drive.generation_run_id),
        autopilot_run_id=drive.autopilot_run_id,
        error_type=type(exc).__name__,
    )
    return RecoveryFailure(drive=drive, reason=_failure_reason(exc))


def _failure_reason(exc: Exception) -> str:
    message = " ".join(str(exc).split()) or type(exc).__name__
    reason = f"{type(exc).__name__}{_REASON_SEPARATOR}{message}"
    return reason[:FAILURE_REASON_MAX_CHARS]


def summary_text(report: ScanReport) -> str:
    """The one message Pedro gets after the scan."""
    text = SUMMARY_SCAN.format(
        recovered=report.recovered, dead=report.still_dead, queued=report.queued
    )
    if report.failures:
        text = f"{text}\n{_failures_summary(report.failures)}"
    if not report.interactive:
        return text
    titles = _TITLE_SEPARATOR.join(
        _short(title) for title in report.interactive[:SUMMARY_TITLES_MAX]
    )
    return f"{text}\n{SUMMARY_INTERACTIVE.format(titles=titles)}"


def _failures_summary(failures: tuple[RecoveryFailure, ...]) -> str:
    items = _TITLE_SEPARATOR.join(
        SUMMARY_FAILURE_ITEM.format(
            run_id=failure.drive.autopilot_run_id, reason=_short(failure.reason)
        )
        for failure in failures[:SUMMARY_TITLES_MAX]
    )
    return SUMMARY_FAILURES.format(items=items)


def _short(title: str) -> str:
    if len(title) <= SUMMARY_TITLE_MAX_CHARS:
        return title
    return title[: SUMMARY_TITLE_MAX_CHARS - 1] + _ELLIPSIS


__all__ = ["DailyRecoveryScan", "DailyScanDependencies", "summary_text"]
