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

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_repair import (
    LOG_EVENT_DRIFT_CONVERGED,
    LOG_EVENT_DRIFT_DETECTED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_AWAITING_HUMAN
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    carousel_run_epoch_var,
)
from rag_backend.domain.protocols.carousel_run import CarouselCheckpointStateGateway
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

logger = structlog.get_logger()

_CHECKPOINT_VALIDATION_KEY = "presentation_validation"
_CHECKPOINT_LOCALIZED_KEY = "localized_slides"
_CHECKPOINT_POLICY_KEY = "presentation_policy_version"
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
        return converged

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
