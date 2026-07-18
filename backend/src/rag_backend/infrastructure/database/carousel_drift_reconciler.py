"""Autonomous projection↔checkpoint drift reconciler for carousels (AE-0311).

Runs in the workflow-workers tick AFTER the reaper (pinned AE-0315 ordering).
A repair that dies between its projection commit and its checkpoint write
leaves a **repaired projection with a stale blocking checkpoint report** — and
"the client retries" assumes a retry nobody guarantees. This watchdog closes
that gap for **in-flight** projects (the checkpoint is what the workflow reads
next, so it MUST converge before the next phase): it detects the divergence,
re-derives the clean localized copy from the authoritative projection, and
writes the checkpoint through the engine wrapper, stamping the row's CURRENT
``run_epoch`` so the fencing guard accepts the tick-owned write.

The repair is idempotent by design, so converging a just-reaped row (its
checkpoint is untouched by the reaper) is safe and epoch-fenced.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

import structlog
from sqlalchemy import CursorResult, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_repair import (
    LOG_EVENT_DRIFT_CONVERGED,
    LOG_EVENT_DRIFT_DETECTED,
)
from rag_backend.domain.constants.carousel_run import (
    LOG_EVENT_PHASE_DRIFT_BLOCKED,
    LOG_EVENT_PHASE_DRIFT_CONVERGED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
)
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    carousel_run_epoch_var,
)
from rag_backend.domain.protocols.carousel_run import CarouselCheckpointStateGateway
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.pg_lock_timeout import (
    apply_run_write_lock_timeout,
)

logger = structlog.get_logger()

_CHECKPOINT_VALIDATION_KEY = "presentation_validation"
_CHECKPOINT_LOCALIZED_KEY = "localized_slides"
_CHECKPOINT_POLICY_KEY = "presentation_policy_version"
_CHECKPOINT_PHASE_KEY = "current_phase"
_CHECKPOINT_PHASE_STATUS_KEY = "phase_status"
_REPORT_BLOCKING_KEY = "blocking"

# Recompute result: repaired slides, the fresh report dict, and whether the
# projection is still blocking after the (idempotent) re-repair.
_Recomputed = tuple[list[dict[str, object]], dict[str, object], bool]


class CarouselDriftReconcilerRepository:
    """ORM-backed implementation of :class:`CarouselDriftReconciler`."""

    def __init__(self, checkpoint: CarouselCheckpointStateGateway) -> None:
        self._checkpoint = checkpoint

    async def reconcile(self, db: AsyncSession) -> int:
        """Converge every in-flight row whose projection outran its checkpoint."""
        rows = await self._parked_in_flight_rows(db)
        converged = 0
        for row in rows:
            if await self._reconcile_row(db, row):
                converged += 1
        converged += await self._reconcile_failed_phase_drift(db)
        return converged

    async def _reconcile_failed_phase_drift(self, db: AsyncSession) -> int:
        """AE-0320: converge rows a dead run left ``failed`` behind a parked
        checkpoint at a DIFFERENT phase.

        A resume run that completed its phase work (checkpoint advanced and
        parked at ``awaiting_human``) but died during finalization marks the
        row ``failed`` at the OLD phase — the UI shows a failure while the
        workflow is actually parked at the next gate. Same-phase failures are
        genuine and stay ``failed`` (the recovery UI owns them).
        """
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.phase_status == PHASE_STATUS_FAILED,
                CarouselProjectModel.status != CarouselStatus.COMPLETED.value,
            )
        )
        converged = 0
        for row in result.scalars().all():
            if await self._converge_failed_row(db, row):
                converged += 1
        return converged

    async def _converge_failed_row(
        self,
        db: AsyncSession,
        row: CarouselProjectModel,
    ) -> bool:
        """Converge one failed row onto its parked checkpoint phase."""
        project_id = str(row.id)
        from_phase = str(row.current_phase or "")
        seen_epoch = int(row.run_epoch or 0)
        state = await self._checkpoint.read_state(project_id)
        target = _parked_checkpoint_phase(state)
        if target is None or target == from_phase:
            return False
        # AE-0320 (external review r1 #6/#7): CAS on run_epoch like the reaper
        # flip (a replacement run's writes must never be clobbered), and the
        # write is savepoint-scoped + lock-timeout-bounded so a locked row can
        # neither wedge the tick nor roll back sibling convergences.
        try:
            async with db.begin_nested():
                await apply_run_write_lock_timeout(db)
                result = await db.execute(
                    update(CarouselProjectModel)
                    .where(
                        CarouselProjectModel.id == project_id,
                        CarouselProjectModel.phase_status == PHASE_STATUS_FAILED,
                        CarouselProjectModel.run_epoch == seen_epoch,
                    )
                    .values(
                        current_phase=target,
                        phase_status=PHASE_STATUS_AWAITING_HUMAN,
                        lock_version=CarouselProjectModel.lock_version + 1,
                        run_epoch=seen_epoch + 1,
                        run_started_at=None,
                        run_heartbeat_at=None,
                    )
                )
        except OperationalError as exc:
            logger.warning(
                LOG_EVENT_PHASE_DRIFT_BLOCKED,
                project_id=project_id,
                error=str(exc),
            )
            return False
        if cast(CursorResult[object], result).rowcount != 1:
            return False
        logger.warning(
            LOG_EVENT_PHASE_DRIFT_CONVERGED,
            project_id=project_id,
            from_phase=from_phase,
            to_phase=target,
        )
        return True

    @staticmethod
    async def _parked_in_flight_rows(db: AsyncSession) -> list[CarouselProjectModel]:
        result = await db.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.phase_status == PHASE_STATUS_AWAITING_HUMAN,
                CarouselProjectModel.status != CarouselStatus.COMPLETED.value,
            )
        )
        return list(result.scalars().all())

    async def _reconcile_row(
        self,
        db: AsyncSession,
        row: CarouselProjectModel,
    ) -> bool:
        """Detect + converge one row; True when a convergence write landed."""
        project_id = str(row.id)
        state = await self._checkpoint.read_state(project_id)
        if not _checkpoint_blocks(state):
            return False
        recomputed = await _recompute_from_projection(db, row)
        if recomputed is None or recomputed[2]:
            return False
        logger.warning(LOG_EVENT_DRIFT_DETECTED, project_id=project_id)
        await self._converge(row, recomputed)
        logger.info(LOG_EVENT_DRIFT_CONVERGED, project_id=project_id)
        return True

    async def _converge(
        self,
        row: CarouselProjectModel,
        recomputed: _Recomputed,
    ) -> None:
        """Write the clean localized copy + report, stamping the current epoch."""
        project_id = str(row.id)
        values = _convergence_values(recomputed, _policy_of(row))
        context = CarouselRunContext(project_id, int(row.run_epoch or 0))
        token = carousel_run_epoch_var.set(context)
        try:
            await self._checkpoint.write_state(project_id, values)
        finally:
            carousel_run_epoch_var.reset(token)


async def _recompute_from_projection(
    db: AsyncSession,
    row: CarouselProjectModel,
) -> _Recomputed | None:
    """Validate the authoritative projection AS-IS (no re-repair).

    The projection is authoritative and — in the AE-0311 drift scenario — was
    already repaired by the failed repair (projection commits first). We only
    converge when it validates clean: a still-blocking projection is not drift
    (it needs the repair endpoint, not a checkpoint overwrite from stale copy).
    """
    from rag_backend.application.services.carousel.carousel_repair_projection import (
        localized_from_slides,
    )
    from rag_backend.application.services.carousel.presentation_review_pipeline import (
        validate_localized_slides,
        validation_report_to_dict,
    )
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    repo = PostgresCarouselRepository(db)
    slides = await repo.get_slides_by_project(UUID(str(row.id)))
    if not slides:
        return None
    localized = localized_from_slides(slides)
    report = validate_localized_slides(localized, policy_version=_policy_of(row))
    return localized, validation_report_to_dict(report), report.blocking


def _policy_of(row: CarouselProjectModel) -> str | None:
    """Read the row's presentation policy version as ``str | None``."""
    value: object = row.presentation_policy_version
    return value if isinstance(value, str) and value.strip() else None


def _parked_checkpoint_phase(state: dict[str, object] | None) -> str | None:
    """Checkpoint phase when it is parked at ``awaiting_human``; else ``None``."""
    if not isinstance(state, dict):
        return None
    status = str(state.get(_CHECKPOINT_PHASE_STATUS_KEY, "") or "")
    if status != PHASE_STATUS_AWAITING_HUMAN:
        return None
    phase = str(state.get(_CHECKPOINT_PHASE_KEY, "") or "")
    return phase or None


def _checkpoint_blocks(state: dict[str, object] | None) -> bool:
    """True when the checkpoint holds a blocking presentation report."""
    if not isinstance(state, dict):
        return False
    report = state.get(_CHECKPOINT_VALIDATION_KEY)
    return isinstance(report, dict) and report.get(_REPORT_BLOCKING_KEY) is True


def _convergence_values(
    recomputed: _Recomputed,
    policy_version: str | None,
) -> dict[str, object]:
    repaired_slides, report, _ = recomputed
    values: dict[str, object] = {
        _CHECKPOINT_LOCALIZED_KEY: repaired_slides,
        _CHECKPOINT_VALIDATION_KEY: report,
    }
    if policy_version:
        values[_CHECKPOINT_POLICY_KEY] = policy_version
    return values


__all__ = ["CarouselDriftReconcilerRepository"]
