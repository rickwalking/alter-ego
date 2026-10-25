"""The daily recovery scan: one pass at 04:00 São Paulo time (PgQueuer schedule).

1. Retry once each autopilot drive the queue parked in the last 7 days for a
   transient-class reason: the dead letter is marked tried first, so a second scan
   (or a second worker) never retries it again, then the autopilot run is revived.
2. Resume the autopilot runs escalated as stale in the last 72 hours.
3. Purge succeeded runs and PgQueuer log rows older than 30 days.
4. Count what is still dead and what is queued, list the parked dashboard projects.
The caller sends Pedro the summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.modules.generation_queue.constants import (
    SCAN_PURGE_DAYS,
    SCAN_RECOVERY_DAYS,
    SCAN_STALE_HOURS,
    SUMMARY_INTERACTIVE,
    SUMMARY_SCAN,
    SUMMARY_TITLE_MAX_CHARS,
    SUMMARY_TITLES_MAX,
)
from rag_backend.modules.generation_queue.domain.ports import Clock
from rag_backend.modules.generation_queue.domain.recovery import (
    ParkedAutopilot,
    RecoveryStore,
    ScanReport,
)

_TITLE_SEPARATOR = "; "
_ELLIPSIS = "…"


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
        recovered = await self._retry_dead_letters(window)
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
        )

    async def _retry_dead_letters(self, since: datetime) -> int:
        recovered = 0
        for drive in await self._deps.store.recoverable(since):
            if not await self._deps.store.mark_attempted(drive.generation_run_id):
                continue
            if await self._deps.autopilot.revive_dead_letter(drive.autopilot_run_id):
                recovered += 1
        return recovered


def summary_text(report: ScanReport) -> str:
    """The one message Pedro gets after the scan."""
    text = SUMMARY_SCAN.format(
        recovered=report.recovered, dead=report.still_dead, queued=report.queued
    )
    if not report.interactive:
        return text
    titles = _TITLE_SEPARATOR.join(
        _short(title) for title in report.interactive[:SUMMARY_TITLES_MAX]
    )
    return f"{text}\n{SUMMARY_INTERACTIVE.format(titles=titles)}"


def _short(title: str) -> str:
    if len(title) <= SUMMARY_TITLE_MAX_CHARS:
        return title
    return title[: SUMMARY_TITLE_MAX_CHARS - 1] + _ELLIPSIS


__all__ = ["DailyRecoveryScan", "DailyScanDependencies", "summary_text"]
