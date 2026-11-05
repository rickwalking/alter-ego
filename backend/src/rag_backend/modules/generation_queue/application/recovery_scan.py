"""The daily recovery scan: one pass at 04:00 São Paulo time (PgQueuer schedule).

1. Retry once each autopilot drive the queue parked in the last 7 days for a
   transient-class reason: marking and reviving commit atomically, and one failed
   item is logged and reported without stopping the others.
2. Resume the autopilot runs escalated as stale in the last 72 hours.
3. Re-send once the escalation notice with Retry to stuck runs that never got it.
4. Purge succeeded runs and PgQueuer log rows older than 30 days.
5. Count what is still dead and what is queued, list the parked dashboard projects.
The caller sends Pedro the summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from rag_backend.modules.generation_queue.constants import (
    LOG_SCAN_ITEM_FAILED,
    SCAN_PURGE_DAYS,
    SCAN_RECOVERY_DAYS,
    SCAN_STALE_HOURS,
    SUMMARY_FAILURE_ITEM,
    SUMMARY_FAILURE_OVERFLOW,
    SUMMARY_FAILURES,
    SUMMARY_INTERACTIVE,
    SUMMARY_SCAN,
    SUMMARY_TITLE_MAX_CHARS,
    SUMMARY_TITLES_MAX,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
from rag_backend.modules.generation_queue.domain.recovery import (
    EscalationRenotifier,
    ParkedAutopilot,
    ParkedDrive,
    RecoveryFailure,
    RecoveryStore,
    RenotifyFailure,
    ScanReport,
    failure_metadata,
)
from rag_backend.modules.generation_queue.renotify_constants import (
    LOG_SCAN_RENOTIFY_FAILED,
    RENOTIFY_LISTING,
    SUMMARY_RENOTIFIED,
    SUMMARY_RENOTIFY_FAILURES,
)

logger = structlog.get_logger()

_TITLE_SEPARATOR = "; "
_ELLIPSIS = "…"


@dataclass(frozen=True, kw_only=True)
class DailyScanDependencies:
    """The queue store, the autopilot bridges and the clock."""

    store: RecoveryStore
    autopilot: ParkedAutopilot
    renotifier: EscalationRenotifier
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
        renotified, renotify_failures = await self._renotify_stuck()
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
            renotified=renotified,
            renotify_failures=renotify_failures,
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

    async def _renotify_stuck(self) -> tuple[int, tuple[RenotifyFailure, ...]]:
        try:
            run_ids = await self._deps.renotifier.stuck_runs()
        except Exception as exc:
            return 0, (_renotify_failure(RENOTIFY_LISTING, exc),)
        renotified = 0
        failures: list[RenotifyFailure] = []
        for run_id in run_ids:
            try:
                sent = await self._deps.renotifier.renotify(run_id)
            except Exception as exc:
                failures.append(_renotify_failure(run_id, exc))
                continue
            renotified += int(sent)
        return renotified, tuple(failures)


def _item_failure(drive: ParkedDrive, exc: Exception) -> RecoveryFailure:
    metadata = failure_metadata(exc)
    logger.warning(
        LOG_SCAN_ITEM_FAILED,
        generation_run_id=str(drive.generation_run_id),
        autopilot_run_id=drive.autopilot_run_id,
        error_type=metadata.exception_type,
        dbapi_type=metadata.dbapi_type,
        sqlstate=metadata.sqlstate,
    )
    return RecoveryFailure(drive=drive, reason=metadata.reason)


def _renotify_failure(run_id: str, exc: Exception) -> RenotifyFailure:
    metadata = failure_metadata(exc)
    logger.warning(
        LOG_SCAN_RENOTIFY_FAILED,
        autopilot_run_id=run_id,
        error_type=metadata.exception_type,
        dbapi_type=metadata.dbapi_type,
        sqlstate=metadata.sqlstate,
    )
    return RenotifyFailure(run_id=run_id, reason=metadata.reason)


def summary_text(report: ScanReport) -> str:
    """The one message Pedro gets after the scan."""
    text = SUMMARY_SCAN.format(
        recovered=report.recovered, dead=report.still_dead, queued=report.queued
    )
    if report.failures:
        text = f"{text}\n{_failures_summary(report.failures)}"
    if report.renotified:
        text = f"{text}\n{SUMMARY_RENOTIFIED.format(count=report.renotified)}"
    if report.renotify_failures:
        text = f"{text}\n{_renotify_failures_summary(report.renotify_failures)}"
    if not report.interactive:
        return text
    titles = _TITLE_SEPARATOR.join(
        _short(title) for title in report.interactive[:SUMMARY_TITLES_MAX]
    )
    return f"{text}\n{SUMMARY_INTERACTIVE.format(titles=titles)}"


def _failures_summary(failures: tuple[RecoveryFailure, ...]) -> str:
    pairs = [(item.drive.autopilot_run_id, item.reason) for item in failures]
    return SUMMARY_FAILURES.format(items=_failure_items(pairs))


def _renotify_failures_summary(failures: tuple[RenotifyFailure, ...]) -> str:
    pairs = [(item.run_id, item.reason) for item in failures]
    return SUMMARY_RENOTIFY_FAILURES.format(items=_failure_items(pairs))


def _failure_items(failures: list[tuple[str, str]]) -> str:
    visible = failures[:SUMMARY_TITLES_MAX]
    items = _TITLE_SEPARATOR.join(
        SUMMARY_FAILURE_ITEM.format(run_id=run_id, reason=_short(reason))
        for run_id, reason in visible
    )
    overflow = len(failures) - len(visible)
    if overflow:
        overflow_text = SUMMARY_FAILURE_OVERFLOW.format(count=overflow)
        items = _TITLE_SEPARATOR.join((items, overflow_text))
    return items


def _short(title: str) -> str:
    if len(title) <= SUMMARY_TITLE_MAX_CHARS:
        return title
    return title[: SUMMARY_TITLE_MAX_CHARS - 1] + _ELLIPSIS


__all__ = ["DailyRecoveryScan", "DailyScanDependencies", "summary_text"]
