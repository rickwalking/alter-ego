"""Completed-project slide-text edit service (AE-0314).

Applies deterministic reviewer text edits to a COMPLETED carousel WITHOUT
regenerating images, landing the change under the shared per-project advisory
lock (AE-0316, the serialization domain shared with AE-0311 repair + AE-0313
republish). The sequence mirrors the repair two-commit contract:

1. Reject an active workflow run, then acquire the advisory lock **non-blocking**
   (a held lock raises the typed ``mutation_in_progress`` conflict) for the WHOLE
   sequence so a concurrent repair/republish serializes.
2. Read the authoritative ``carousel_slides`` projection, merge the reviewer
   edits by slide index, then run the deterministic repair pass over the merged
   copy and re-validate (severity-aware, policy-versioned). The repair pass is
   the AE-0327 clobber guard: clients naturally build edit payloads from the
   checkpoint-backed state endpoint, which is STALER than a repaired
   projection — a whole-locale payload replace would silently reintroduce the
   casing violations POST /repair fixed (the 2026-07-22 prod incident; the
   manual recovery was "re-run repair after any PATCH"). Repair is idempotent
   and only uppercases/canonicalizes, so intentional reviewer fixes survive.
3. ``lock_version`` compare-and-swap, then write the projection + stamp the
   persisted ``needs_republish`` marker in ONE transaction.
4. Converge the checkpoint (source-of-truth option (a), pinned): write the edited
   copy + fresh report through ``patch_parked_checkpoint`` (``as_node=None`` so
   the approved-hold park is preserved). Legacy END-state/absent threads skip the
   checkpoint write (``checkpoint_updated=False``) — the projection is
   authoritative and the republish serves the corrected PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_pipeline import (
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
from rag_backend.application.services.carousel.presentation_review_edits import (
    merge_localized_slide_edits,
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
from rag_backend.domain.constants.carousel_repair import AUDIT_AGGREGATE_CAROUSEL
from rag_backend.domain.constants.carousel_slide_edit import (
    AUDIT_EVENT_SLIDE_EDITED,
    LOG_EVENT_SLIDE_EDITED,
    SLIDE_EDIT_STATUS_UPDATED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
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
class SlideEditCommand:
    """Inputs for one completed-project slide edit (values from the row)."""

    project_id: str
    phase_status: str
    lock_version: int
    policy_version: str | None
    actor_user_id: str
    edited_slides: list[dict[str, object]]


@dataclass(frozen=True)
class SlideEditResult:
    """Outcome of an edit: fresh report, updated rows, marker, convergence."""

    status: str
    report: dict[str, object]
    updated_slides: tuple[int, ...]
    needs_republish: bool
    checkpoint_updated: bool


@dataclass(frozen=True)
class CarouselSlideEditDeps:
    """Collaborators for the slide-edit service, sharing one request session."""

    db: AsyncSession
    workflow_service: EditorialWorkflowService
    repo: CarouselRepository
    events: WorkflowEventService | None = None


class CarouselSlideEditService:
    """Applies deterministic completed-project text edits under the shared lock."""

    def __init__(self, deps: CarouselSlideEditDeps) -> None:
        self._db = deps.db
        self._workflow = deps.workflow_service
        self._repo = deps.repo
        self._events = deps.events

    async def edit(self, command: SlideEditCommand) -> SlideEditResult:
        """Run the edit under the run-active guard and the advisory lock."""
        _reject_if_run_active(command.phase_status)
        engine = engine_from_session(self._db)
        async with carousel_project_lock(engine, command.project_id, blocking=False):
            return await self._edit_locked(command)

    async def _edit_locked(self, command: SlideEditCommand) -> SlideEditResult:
        """Gather → merge → repair → validate → persist inside the critical section."""
        slides = await self._repo.get_slides_by_project(UUID(command.project_id))
        merged = merge_localized_slide_edits(
            localized_from_slides(slides), command.edited_slides
        )
        # AE-0327: repair the merged copy in the SAME transaction so a stale
        # client payload cannot reintroduce violations a prior repair fixed.
        repair = await compute_localized_repairs(
            merged, policy_version=command.policy_version
        )
        merged = repair.repaired_slides
        report = repair.report
        await self._take_cas(command)
        updated = await apply_localized_to_slides(self._repo, slides, merged)
        await CarouselProjectWriteOwner(self._db).mark_needs_republish(
            command.project_id
        )
        await self._emit_audit(command, updated)
        await self._db.commit()
        checkpoint_updated = await self._write_checkpoint(command, merged, report)
        logger.info(
            LOG_EVENT_SLIDE_EDITED,
            project_id=command.project_id,
            slide_indexes=list(updated),
            casing_repairs=len(repair.diffs),
            checkpoint_updated=checkpoint_updated,
        )
        return SlideEditResult(
            status=SLIDE_EDIT_STATUS_UPDATED,
            report=report,
            updated_slides=updated,
            needs_republish=True,
            checkpoint_updated=checkpoint_updated,
        )

    async def _take_cas(self, command: SlideEditCommand) -> None:
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
        command: SlideEditCommand,
        merged: list[dict[str, object]],
        report: dict[str, object],
    ) -> bool:
        """Converge the parked checkpoint (option (a); park-preserving write)."""
        values: dict[str, object] = {
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: merged,
            WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: report,
        }
        if command.policy_version:
            values[WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY] = (
                command.policy_version
            )
        return await self._workflow.patch_parked_checkpoint(command.project_id, values)

    async def _emit_audit(
        self,
        command: SlideEditCommand,
        updated_numbers: tuple[int, ...],
    ) -> None:
        """Emit the slide-edit audit event via the existing workflow audit path."""
        if self._events is None:
            return
        await self._events.emit(
            self._db,
            event_type=AUDIT_EVENT_SLIDE_EDITED,
            aggregate_id=command.project_id,
            aggregate_type=AUDIT_AGGREGATE_CAROUSEL,
            payload={"slide_indexes": list(updated_numbers)},
            metadata={"actor_user_id": command.actor_user_id},
        )


def _reject_if_run_active(phase_status: str) -> None:
    """A carousel with an active run must not be edited concurrently."""
    if phase_status == PHASE_STATUS_IN_PROGRESS:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )


__all__ = [
    "CarouselSlideEditDeps",
    "CarouselSlideEditService",
    "SlideEditCommand",
    "SlideEditResult",
]
