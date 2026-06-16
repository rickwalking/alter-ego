"""Workflow Kanban board API (UI-018).

Thin HTTP adapter (AE-0131). The phase-column aggregation reads the carousel
rows through the publishing facade's read projection (the sole carousel/blog ORM
read seam behind the :class:`PublishingReadPort`); this route imports no carousel
ORM. The admin/owner-or-reviewer scope is resolved at the edge and passed to the
projection as the ``author_id`` filter, then the projection columns are mapped
one-to-one onto the existing ``WorkflowKanbanResponse`` schema (byte-identical).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireWorkflowBoard
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.deps import get_carousel_repo
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.domain.models.user import UserRole
from rag_backend.modules.publishing import (
    BOARD_PHASES,
    BoardColumn,
    BoardQuery,
    CarouselRepository,
    PublishingModule,
)

router = APIRouter(tags=["workflow_board"], dependencies=[RequireWorkflowBoard])

# Re-exported (object-identity) from the publishing facade so the legacy
# ``KANBAN_PHASES`` symbol keeps resolving for existing importers; the column
# ordering is owned by the publishing module (single source of truth).
KANBAN_PHASES = BOARD_PHASES


def _get_publishing_module(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the workflow-board edge."""
    return build_publishing_module(
        PublishingComposition(session=db, carousel_repository=repo, with_read=True),
    )


class KanbanCardResponse(BaseModel):
    """Single project card on the Kanban board."""

    id: str
    title: str
    topic: str
    current_phase: str
    phase_status: str
    workflow_status: str | None = None
    updated_at: str | None = None


class KanbanColumnResponse(BaseModel):
    """Kanban column grouped by workflow phase."""

    phase: str
    cards: list[KanbanCardResponse] = Field(default_factory=list)


class WorkflowKanbanResponse(BaseModel):
    """Full Kanban board."""

    columns: list[KanbanColumnResponse]


def _to_column_response(column: BoardColumn) -> KanbanColumnResponse:
    """Map a board projection column one-to-one onto the legacy response schema."""
    return KanbanColumnResponse(
        phase=column.phase,
        cards=[
            KanbanCardResponse(
                id=card.id,
                title=card.title,
                topic=card.topic,
                current_phase=card.current_phase,
                phase_status=card.phase_status,
                workflow_status=card.workflow_status,
                updated_at=card.updated_at,
            )
            for card in column.cards
        ],
    )


@router.get(
    "/workflow-board",
    response_model=WorkflowKanbanResponse,
    summary="Get workflow Kanban board",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_workflow_kanban(
    request: Request,
    current_user: EditorUser,
    publishing: Annotated[PublishingModule, Depends(_get_publishing_module)],
) -> WorkflowKanbanResponse:
    """Return projects grouped by workflow phase (UI-018)."""
    author_filter = (
        None if current_user.role == UserRole.ADMIN.value else current_user.id
    )
    projection = await publishing.service.project_board(
        BoardQuery(author_id=author_filter),
    )
    return WorkflowKanbanResponse(
        columns=[_to_column_response(column) for column in projection.columns],
    )


__all__ = ["router"]
