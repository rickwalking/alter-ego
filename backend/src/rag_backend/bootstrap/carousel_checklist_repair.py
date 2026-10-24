"""Composition root of the one-shot checklist item repair.

The plan reads the ``carousel_slides`` projection and the same layout rule the
renderer uses. The apply writes through the slide-edit service behind
``PATCH /api/carousels/{id}/slides`` (advisory lock, ``lock_version`` CAS,
projection write, ``needs_republish`` marker, checkpoint patch), then runs the
republish service behind ``POST /api/carousels/{id}/republish`` on a fresh
session and clears the marker when it succeeds. A failed republish leaves the
marker set, so the republish sweeper retries it. A run in progress or a held
project lock is reported as an error and nothing is written.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.agents.harness.checkpointer import build_checkpointer
from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.carousel_republish import (
    republish_completed_carousel,
)
from rag_backend.application.services.carousel.carousel_slide_edit_service import (
    CarouselSlideEditDeps,
    CarouselSlideEditService,
    SlideEditCommand,
)
from rag_backend.application.services.carousel.checklist_item_repair import (
    ChecklistItemMove,
    ChecklistRepairPlan,
    plan_checklist_repair,
)
from rag_backend.application.services.carousel_template.role_layouts import (
    checklist_slide_numbers,
)
from rag_backend.bootstrap.autopilot_worker_factory import autopilot_engine_factory
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.carousel_conflict import CarouselConflictError
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.public import CarouselProjectWriteOwner

CHECKLIST_REPAIR_ACTOR = "system:ae-0543-checklist-repair"
ERR_PROJECT_NOT_FOUND = "project not found"
ERR_PROJECT_NOT_COMPLETED = "project is not completed"

SessionMaker = async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class ChecklistRepairRequest:
    """Which carousel to repair, and whether to write."""

    project_id: UUID
    apply: bool


@dataclass(frozen=True)
class ChecklistRepairReport:
    """What the run found and did."""

    project_id: str
    moves: tuple[ChecklistItemMove, ...] = ()
    applied: bool = False
    republished: bool = False
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Loaded:
    project: CarouselProject
    lock_version: int
    plan: ChecklistRepairPlan


async def _load(db: AsyncSession, project_id: UUID) -> _Loaded | None:
    """The project row and its repair plan, ``None`` when the project is missing."""
    row = await db.get(CarouselProjectModel, str(project_id))
    if row is None:
        return None
    slides = await PostgresCarouselRepository(db).get_slides_by_project(project_id)
    project = row.to_entity()
    numbers = checklist_slide_numbers(
        project, {slide.slide_number: slide.slide_type for slide in slides}
    )
    plan = plan_checklist_repair(localized_from_slides(slides), numbers)
    return _Loaded(project=project, lock_version=int(row.lock_version or 1), plan=plan)


async def _edit(db: AsyncSession, loaded: _Loaded) -> None:
    """Write the plan through the slide-edit service (projection + checkpoint)."""
    async with AsyncExitStack() as stack:
        checkpointer = await build_checkpointer(get_settings(), stack)
        workflow = autopilot_engine_factory(checkpointer)()
        service = CarouselSlideEditService(
            CarouselSlideEditDeps(
                db=db,
                workflow_service=workflow,
                repo=PostgresCarouselRepository(db),
                events=workflow.events,
            )
        )
        project = loaded.project
        await service.edit(
            SlideEditCommand(
                project_id=str(project.id),
                phase_status=project.phase_status,
                lock_version=loaded.lock_version,
                policy_version=project.presentation_policy_version,
                actor_user_id=project.owner_id or CHECKLIST_REPAIR_ACTOR,
                edited_slides=loaded.plan.edited_slides,
            )
        )


async def _republish(maker: SessionMaker, project_id: str) -> tuple[str, ...]:
    """Rebuild the artifacts; clears the marker on success, else returns the errors."""
    async with maker() as db:
        result = await republish_completed_carousel(db, project_id)
        if not result.completed:
            return result.errors
        await CarouselProjectWriteOwner(db).clear_needs_republish(project_id)
        await db.commit()
    return ()


async def repair_checklist_items(
    maker: SessionMaker, request: ChecklistRepairRequest
) -> ChecklistRepairReport:
    """Plan, and with ``apply`` edit and republish, one carousel's checklist items."""
    project_id = str(request.project_id)
    async with maker() as db:
        loaded = await _load(db, request.project_id)
        if loaded is None:
            return ChecklistRepairReport(project_id, errors=(ERR_PROJECT_NOT_FOUND,))
        moves = loaded.plan.moves
        if not request.apply or not moves:
            return ChecklistRepairReport(project_id, moves=moves)
        if loaded.project.status != CarouselStatus.COMPLETED:
            return ChecklistRepairReport(
                project_id, moves=moves, errors=(ERR_PROJECT_NOT_COMPLETED,)
            )
        try:
            await _edit(db, loaded)
        except CarouselConflictError as conflict:
            return ChecklistRepairReport(
                project_id, moves=moves, errors=(conflict.conflict.code,)
            )
    errors = await _republish(maker, project_id)
    return ChecklistRepairReport(
        project_id, moves=moves, applied=True, republished=not errors, errors=errors
    )


__all__ = [
    "ChecklistRepairReport",
    "ChecklistRepairRequest",
    "repair_checklist_items",
]
