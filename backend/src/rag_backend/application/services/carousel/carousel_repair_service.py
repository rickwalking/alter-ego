"""Deterministic carousel repair service — the two-commit contract (AE-0311).

Runs the bounded deterministic repair pipeline over a carousel's localized
slides and lands the fix under the shared per-project advisory lock (AE-0316,
serialization domain shared with AE-0313 republish + AE-0314 slide edit):

1. Acquire the session-scoped advisory lock **non-blocking** at entry — a held
   lock raises the typed ``mutation_in_progress`` conflict. Held across the
   WHOLE sequence so the seam between the two commits is inside the critical
   section.
2. Take the ``lock_version`` CAS before mutating — a concurrent resume that
   bumped the version loses (``version_conflict``), not races (the bare
   in-progress read is TOCTOU-vulnerable).
3. Write the ``carousel_slides`` projection first, in its own transaction.
4. Write the repaired copy + the FRESH severity-aware validation report in ONE
   engine ``update_state`` call (the checkpoint never holds repaired copy with
   a stale blocking report).
5. Reconciliation check; on partial failure the result reports which store was
   updated so the idempotent retry — and the autonomous drift reconciler —
   converge both stores.

Authority rule: completed → projection authoritative (a projection-only
success already serves correct PDFs, and ``needs_republish`` tells the client
to rebuild); in-flight → the checkpoint is what the workflow reads next, so it
is converged in the same call.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_pipeline import (
    RepairComputation,
    RepairSlideDiff,
    compute_localized_repairs,
)
from rag_backend.application.services.carousel.carousel_repair_projection import (
    apply_localized_to_slides,
    localized_from_slides,
)
from rag_backend.application.services.carousel.carousel_republish import (
    engine_from_session,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_repair import (
    AUDIT_AGGREGATE_CAROUSEL,
    AUDIT_EVENT_REPAIR_APPLIED,
    LOG_EVENT_REPAIR_APPLIED,
    LOG_EVENT_REPAIR_NOOP,
    REPAIR_STATUS_NOOP,
    REPAIR_STATUS_REPAIRED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel import CarouselSlide, CarouselStatus
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    carousel_project_lock,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RepairCarouselCommand:
    """Inputs for one repair invocation (values snapshotted from the row)."""

    project_id: str
    status: str
    phase_status: str
    lock_version: int
    policy_version: str | None
    actor_user_id: str


@dataclass(frozen=True)
class RepairResult:
    """Outcome of a repair: diffs, fresh report, and store convergence flags."""

    status: str
    diffs: tuple[RepairSlideDiff, ...]
    report: dict[str, object]
    needs_republish: bool
    projection_updated: bool
    checkpoint_updated: bool


@dataclass(frozen=True)
class _RepairSource:
    """Gathered repair source: localized copy + its projection rows."""

    localized: list[dict[str, object]]
    policy_version: str | None
    slides: list[CarouselSlide]
    completed: bool


@dataclass(frozen=True)
class _MutationOutcome:
    """What the two-commit mutation actually wrote (for logging)."""

    updated_numbers: tuple[int, ...]
    checkpoint_updated: bool


@dataclass(frozen=True)
class CarouselRepairDeps:
    """Collaborators for the repair service, sharing one request session."""

    db: AsyncSession
    workflow_service: EditorialWorkflowService
    repo: CarouselRepository
    events: WorkflowEventService | None = None


class CarouselRepairService:
    """Applies deterministic repairs to both stores under the shared lock."""

    def __init__(self, deps: CarouselRepairDeps) -> None:
        self._db = deps.db
        self._workflow = deps.workflow_service
        self._repo = deps.repo
        self._events = deps.events

    async def repair(self, command: RepairCarouselCommand) -> RepairResult:
        """Run the repair under the run-active guard and the advisory lock."""
        _reject_if_run_active(command.phase_status)
        engine = engine_from_session(self._db)
        async with carousel_project_lock(engine, command.project_id, blocking=False):
            return await self._repair_locked(command)

    async def _repair_locked(self, command: RepairCarouselCommand) -> RepairResult:
        """Gather → compute → (no-op | mutate) inside the critical section."""
        source = await self._gather(command)
        computation = await compute_localized_repairs(
            source.localized, policy_version=source.policy_version
        )
        if not computation.changed:
            logger.info(
                LOG_EVENT_REPAIR_NOOP,
                project_id=command.project_id,
                blocking=computation.blocking,
            )
            return RepairResult(
                status=REPAIR_STATUS_NOOP,
                diffs=computation.diffs,
                report=computation.report,
                needs_republish=False,
                projection_updated=False,
                checkpoint_updated=False,
            )
        return await self._mutate(command, source, computation)

    async def _gather(self, command: RepairCarouselCommand) -> _RepairSource:
        """Read the repair source: projection for completed, checkpoint else."""
        completed = command.status == CarouselStatus.COMPLETED.value
        slides = await self._repo.get_slides_by_project(UUID(command.project_id))
        if completed:
            return _RepairSource(
                localized=localized_from_slides(slides),
                policy_version=command.policy_version,
                slides=slides,
                completed=True,
            )
        state = await self._workflow.get_workflow_state(command.project_id)
        return _RepairSource(
            localized=_localized_from_state(state),
            policy_version=_policy_from_state(state) or command.policy_version,
            slides=slides,
            completed=False,
        )

    async def _mutate(
        self,
        command: RepairCarouselCommand,
        source: _RepairSource,
        computation: RepairComputation,
    ) -> RepairResult:
        """CAS → projection commit → checkpoint write → reconcile → report."""
        await self._take_cas(command)
        updated_numbers = await apply_localized_to_slides(
            self._repo, source.slides, computation.repaired_slides
        )
        await self._emit_audit(command, computation, updated_numbers)
        await self._db.commit()
        checkpoint_updated = await self._write_checkpoint(command, source, computation)
        _log_repair(
            command,
            computation,
            _MutationOutcome(updated_numbers, checkpoint_updated),
        )
        return RepairResult(
            status=REPAIR_STATUS_REPAIRED,
            diffs=computation.diffs,
            report=computation.report,
            needs_republish=source.completed,
            projection_updated=True,
            checkpoint_updated=checkpoint_updated,
        )

    async def _take_cas(self, command: RepairCarouselCommand) -> None:
        """Atomic ``lock_version`` compare-and-swap; a lost race raises 409."""
        try:
            await CarouselProjectWriteOwner(self._db).bump_resume_lock_version(
                command.project_id, command.lock_version
            )
        except ValueError as exc:
            if str(exc) == ERR_VERSION_CONFLICT:
                raise CarouselConflictError(
                    CarouselConflict.for_code(CONFLICT_CODE_VERSION_CONFLICT)
                ) from None
            raise

    async def _write_checkpoint(
        self,
        command: RepairCarouselCommand,
        source: _RepairSource,
        computation: RepairComputation,
    ) -> bool:
        """Converge the checkpoint for in-flight projects (one update_state)."""
        if source.completed:
            return False
        await self._workflow.update_workflow_state(
            command.project_id,
            _checkpoint_values(source, computation),
        )
        return True

    async def _emit_audit(
        self,
        command: RepairCarouselCommand,
        computation: RepairComputation,
        updated_numbers: tuple[int, ...],
    ) -> None:
        """Emit the repair audit event via the existing workflow audit path."""
        if self._events is None:
            return
        await self._events.emit(
            self._db,
            event_type=AUDIT_EVENT_REPAIR_APPLIED,
            aggregate_id=command.project_id,
            aggregate_type=AUDIT_AGGREGATE_CAROUSEL,
            payload={
                "slide_indexes": list(updated_numbers),
                "rule_codes": _fixed_rule_codes(computation),
                "status": REPAIR_STATUS_REPAIRED,
            },
            metadata={"actor_user_id": command.actor_user_id},
        )


def _checkpoint_values(
    source: _RepairSource,
    computation: RepairComputation,
) -> dict[str, object]:
    """The single-call checkpoint patch: repaired copy + fresh report."""
    values: dict[str, object] = {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: computation.repaired_slides,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: computation.report,
    }
    if source.policy_version:
        values[WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY] = source.policy_version
    return values


def _reject_if_run_active(phase_status: str) -> None:
    """A carousel with an active run must not be repaired concurrently."""
    if phase_status == PHASE_STATUS_IN_PROGRESS:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )


def _localized_from_state(state: object) -> list[dict[str, object]]:
    if not isinstance(state, dict):
        return []
    raw = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(raw, list):
        return []
    return [slide for slide in raw if isinstance(slide, dict)]


def _policy_from_state(state: object) -> str | None:
    if not isinstance(state, dict):
        return None
    value = state.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    return value if isinstance(value, str) and value.strip() else None


def _fixed_rule_codes(computation: RepairComputation) -> list[str]:
    codes: set[str] = set()
    for diff in computation.diffs:
        codes.update(diff.repaired_codes)
    return sorted(codes)


def _log_repair(
    command: RepairCarouselCommand,
    computation: RepairComputation,
    outcome: _MutationOutcome,
) -> None:
    logger.info(
        LOG_EVENT_REPAIR_APPLIED,
        project_id=command.project_id,
        slide_indexes=list(outcome.updated_numbers),
        rule_codes=_fixed_rule_codes(computation),
        checkpoint_updated=outcome.checkpoint_updated,
    )


__all__ = [
    "CarouselRepairDeps",
    "CarouselRepairService",
    "RepairCarouselCommand",
    "RepairResult",
]
