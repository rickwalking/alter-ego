"""Workflow Kanban board API (UI-018).

Thin HTTP adapter. The phase-column aggregation reads the carousel
rows through the publishing facade's read projection (the sole carousel/blog ORM
read seam behind the :class:`PublishingReadPort`); this route imports no carousel
ORM. The admin/owner-or-reviewer scope is resolved at the edge and passed to the
projection as the ``author_id`` filter, then the projection columns are mapped
one-to-one onto the existing ``WorkflowKanbanResponse`` schema (byte-identical).

KANBAN_PHASES is re-exported (same object) from the publishing facade so the legacy
symbol keeps resolving; the publishing module owns the column ordering.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
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

KANBAN_PHASES = BOARD_PHASES


def _get_publishing_module(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the workflow-board edge."""
    return build_publishing_module(
        PublishingComposition(session=db, carousel_repository=repo, with_read=True),
    )


def get_board_query(
    current_user: EditorUser,
    *,
    archived: Annotated[bool, Query()] = False,
) -> BoardQuery:
    """The board scope of the caller: all projects for an admin, else their own."""
    author_filter = (
        None if current_user.role == UserRole.ADMIN.value else current_user.id
    )
    return BoardQuery(author_id=author_filter, archived=archived)


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
    board: Annotated[BoardQuery, Depends(get_board_query)],
    publishing: Annotated[PublishingModule, Depends(_get_publishing_module)],
) -> WorkflowKanbanResponse:
    """Return projects grouped by workflow phase (UI-018).

    Archived carousels are left out; ``archived=true`` lists only them.
    """
    projection = await publishing.service.project_board(board)
    return WorkflowKanbanResponse(
        columns=[_to_column_response(column) for column in projection.columns],
    )


__all__ = ["router"]
