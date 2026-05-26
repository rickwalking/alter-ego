"""Workflow Kanban board API (UI-018)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireWorkflowBoard
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

router = APIRouter(tags=["workflow_board"], dependencies=[RequireWorkflowBoard])

KANBAN_PHASES = [
    PHASE_BRIEF,
    PHASE_RESEARCH,
    PHASE_OUTLINE,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_FINAL_REVIEW,
]


class KanbanCardResponse(BaseModel):
    """Single project card on the Kanban board."""

    id: str
    title: str
    topic: str
    current_phase: str
    phase_status: str
    updated_at: str | None = None


class KanbanColumnResponse(BaseModel):
    """Kanban column grouped by workflow phase."""

    phase: str
    cards: list[KanbanCardResponse] = Field(default_factory=list)


class WorkflowKanbanResponse(BaseModel):
    """Full Kanban board."""

    columns: list[KanbanColumnResponse]


@router.get(
    "/workflow-board",
    response_model=WorkflowKanbanResponse,
    summary="Get workflow Kanban board",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_workflow_kanban(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> WorkflowKanbanResponse:
    """Return projects grouped by workflow phase (UI-018)."""
    query = select(CarouselProjectModel)
    if current_user.role != UserRole.ADMIN.value:
        query = query.where(CarouselProjectModel.owner_id == current_user.id)
    result = await db.execute(query)
    projects = list(result.scalars().all())

    cards_by_phase: dict[str, list[KanbanCardResponse]] = {
        phase: [] for phase in KANBAN_PHASES
    }
    for project in projects:
        phase = project.current_phase or PHASE_BRIEF
        if phase not in cards_by_phase:
            cards_by_phase[phase] = []
        cards_by_phase[phase].append(
            KanbanCardResponse(
                id=str(project.id),
                title=project.title or project.topic,
                topic=project.topic,
                current_phase=phase,
                phase_status=project.phase_status or "pending",
                updated_at=project.updated_at.isoformat()
                if project.updated_at
                else None,
            )
        )

    columns = [
        KanbanColumnResponse(phase=phase, cards=cards_by_phase.get(phase, []))
        for phase in KANBAN_PHASES
    ]
    return WorkflowKanbanResponse(columns=columns)


__all__ = ["router"]
