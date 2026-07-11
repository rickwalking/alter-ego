"""Liveness-keyed stale-run reaper for carousel workflows (AE-0315).

Runs FIRST inside the workflow-workers tick (pinned ordering: the AE-0311
drift reconciler runs after it, only for rows this reaper did not touch this
tick). Rules — pinned by six cold-critic rounds, do not relax:

- Only ``phase_status == in_progress`` rows are ever considered; leftover
  ``run_started_at`` on any other status is ignored.
- **NULL heartbeat is alert-only forever** (migration-day safety: a run alive
  across the deploy that added the column would otherwise be reaped alive on
  the first tick). A row becomes reapable only after a heartbeat has been
  observed and then gone stale.
- A reap requires **N consecutive stale observations** (default 3) so a
  transient DB blip on the heartbeat UPDATE never looks like death. The
  observation counts live in worker-scoped memory (``self._stale_counts``):
  a process restart resets them, which only delays a reap by up to N ticks —
  an accepted trade-off pinned by the ticket (no extra column).
- Wall-clock age past the overdue threshold triggers the ``run_overdue``
  alert ONLY — never a reap by itself (slow-but-alive runs keep running).
- The flip is ONE atomic UPDATE: ``phase_status`` reconciled against the
  checkpoint (parked → mirror it; mid-step/unknown → ``awaiting_human``),
  ``lock_version`` AND ``run_epoch`` bumped (fencing zombies + failing any
  in-flight repair/resume CAS), run columns cleared. The reaper NEVER
  touches checkpoint state: a "clean re-resume" means LangGraph re-executes
  the interrupted node from its start, which is safe because side effects
  before ``interrupt()`` are idempotent by project rule (CLAUDE.md).
- Where the dying task's asyncio handle is known in-process, it is cancelled
  by reference (best-effort; the epoch fence is the correctness guarantee).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

import structlog
from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_run import (
    LOG_EVENT_RUN_NULL_HEARTBEAT,
    LOG_EVENT_RUN_OVERDUE,
    LOG_EVENT_RUN_REAPED,
    RUN_FINISHED_REASON_STALE,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.protocols.carousel_run import (
    CarouselCheckpointPhaseStatusReader,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

logger = structlog.get_logger()


def _as_utc(value: datetime) -> datetime:
    """Normalize naive timestamps (SQLite) to aware UTC for comparisons."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


@dataclass(frozen=True)
class CarouselRunReaperConfig:
    """Reaper thresholds (from Settings at the composition root)."""

    heartbeat_stale_seconds: int
    reap_observations: int
    overdue_minutes: int


class CarouselRunReaperRepository:
    """ORM-backed implementation of :class:`CarouselStaleRunReaper`."""

    def __init__(
        self,
        config: CarouselRunReaperConfig,
        checkpoint_reader: CarouselCheckpointPhaseStatusReader | None = None,
    ) -> None:
        self._config = config
        self._checkpoint_reader = checkpoint_reader
        # Worker-scoped consecutive-stale-observation memory (see module doc).
        self._stale_counts: dict[str, int] = {}

    async def tick(self, db: AsyncSession) -> int:
        """One watchdog observation pass over all in_progress rows."""
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.phase_status == PHASE_STATUS_IN_PROGRESS
            )
        )
        rows = list(result.scalars().all())
        active_ids = {str(row.id) for row in rows}
        for tracked_id in list(self._stale_counts):
            if tracked_id not in active_ids:
                del self._stale_counts[tracked_id]
        reaped = 0
        now = datetime.now(UTC)
        for row in rows:
            if await self._observe_row(db, row, now):
                reaped += 1
        return reaped

    async def _observe_row(
        self,
        db: AsyncSession,
        row: CarouselProjectModel,
        now: datetime,
    ) -> bool:
        """Observe one in_progress row; True when it was reaped."""
        project_id = str(row.id)
        self._alert_if_overdue(row, now)
        if row.run_heartbeat_at is None:
            logger.warning(LOG_EVENT_RUN_NULL_HEARTBEAT, project_id=project_id)
            self._stale_counts.pop(project_id, None)
            return False
        stale_after = timedelta(seconds=self._config.heartbeat_stale_seconds)
        if now - _as_utc(row.run_heartbeat_at) <= stale_after:
            self._stale_counts.pop(project_id, None)
            return False
        observed = self._stale_counts.get(project_id, 0) + 1
        self._stale_counts[project_id] = observed
        if observed < self._config.reap_observations:
            return False
        return await self._reap(db, row)

    def _alert_if_overdue(self, row: CarouselProjectModel, now: datetime) -> None:
        """Wall-clock overdue alert (never a reap by itself)."""
        if row.run_started_at is None:
            return
        elapsed = now - _as_utc(row.run_started_at)
        if elapsed <= timedelta(minutes=self._config.overdue_minutes):
            return
        logger.warning(
            LOG_EVENT_RUN_OVERDUE,
            project_id=str(row.id),
            elapsed_minutes=int(elapsed.total_seconds() // 60),
            current_phase=row.current_phase,
        )

    async def _reconciled_phase_status(self, project_id: str) -> str:
        """Checkpoint reconciliation: parked → mirror; mid-step → awaiting_human."""
        if self._checkpoint_reader is None:
            return PHASE_STATUS_AWAITING_HUMAN
        try:
            checkpoint_status = await self._checkpoint_reader(project_id)
        except Exception:
            logger.exception("carousel_run_reap_checkpoint_read_failed", exc_info=True)
            return PHASE_STATUS_AWAITING_HUMAN
        if checkpoint_status and checkpoint_status != PHASE_STATUS_IN_PROGRESS:
            return checkpoint_status
        return PHASE_STATUS_AWAITING_HUMAN

    async def _reap(self, db: AsyncSession, row: CarouselProjectModel) -> bool:
        """Fence + flip in ONE atomic UPDATE, then cancel/publish."""
        project_id = str(row.id)
        seen_epoch = int(row.run_epoch or 0)
        reconciled = await self._reconciled_phase_status(project_id)
        # Enumerated raw-SQL site (write-site survey §2 #20): the CAS on
        # phase_status + run_epoch makes the flip race-safe without the
        # advisory lock; the lock_version bump fails any in-flight
        # repair/resume CAS holding the old version.
        result = await db.execute(
            update(CarouselProjectModel)
            .where(
                CarouselProjectModel.id == project_id,
                CarouselProjectModel.phase_status == PHASE_STATUS_IN_PROGRESS,
                CarouselProjectModel.run_epoch == seen_epoch,
            )
            .values(
                phase_status=reconciled,
                lock_version=CarouselProjectModel.lock_version + 1,
                run_epoch=seen_epoch + 1,
                run_started_at=None,
                run_heartbeat_at=None,
            )
        )
        if cast(CursorResult[object], result).rowcount != 1:
            return False
        self._stale_counts.pop(project_id, None)
        await self._finalize_reap(project_id, reconciled)
        return True

    @staticmethod
    async def _finalize_reap(project_id: str, reconciled: str) -> None:
        """Best-effort task cancel + run.finished(stale) + alert log."""
        from rag_backend.application.services.carousel import (
            editorial_workflow_resume_runner as resume_runner,
        )
        from rag_backend.application.services.carousel import (
            editorial_workflow_run_events as run_events,
        )

        cancelled = resume_runner.cancel_background_resume_task(project_id)
        await run_events.publish_run_finished(
            project_id,
            RUN_FINISHED_REASON_STALE,
            final_phase_status=reconciled,
        )
        logger.warning(
            LOG_EVENT_RUN_REAPED,
            project_id=project_id,
            reconciled_phase_status=reconciled,
            task_cancelled=cancelled,
        )


__all__ = ["CarouselRunReaperConfig", "CarouselRunReaperRepository"]
