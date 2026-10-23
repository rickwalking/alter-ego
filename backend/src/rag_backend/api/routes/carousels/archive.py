"""Carousel archive and restore routes (Pedro's decision).

Thin HTTP adapter: the owner (or an admin) archives a carousel they gave up on,
which takes it off the workflow board and out of the workflow alerts, and can
restore it later. Archiving only sets ``archived_at``; the phase and status are
kept, so a restore puts the carousel back where it was. A published carousel or
one whose phase is in progress cannot be archived (409). Both routes are
idempotent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas import ErrorResponse
from rag_backend.api.schemas.carousel_archive import CarouselArchiveResponse
from rag_backend.domain.carousel_archive import archive_refusal
from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.carousel_archive import (
    ARCHIVE_REFUSED_IN_PROGRESS,
    ARCHIVE_REFUSED_PUBLISHED,
    ERR_ARCHIVE_IN_PROGRESS,
    ERR_ARCHIVE_PUBLISHED,
)

router = APIRouter(tags=["carousels-archive"])

_REFUSAL_DETAIL = {
    ARCHIVE_REFUSED_IN_PROGRESS: ERR_ARCHIVE_IN_PROGRESS,
    ARCHIVE_REFUSED_PUBLISHED: ERR_ARCHIVE_PUBLISHED,
}
_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not the owner"},
    404: {"model": ErrorResponse, "description": "Carousel not found"},
}


def _aware(moment: datetime | None) -> datetime | None:
    """The archive time as UTC, also when the database returned it naive."""
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=UTC)


@router.post(
    "/{project_id}/archive",
    response_model=CarouselArchiveResponse,
    summary="Archive a carousel (off the board, no alerts)",
    responses={
        **_RESPONSES,
        409: {"model": ErrorResponse, "description": "Published or in progress"},
    },
)
async def archive_carousel(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> CarouselArchiveResponse:
    """Archive the carousel; an archived one keeps its first archive time."""
    project = await get_carousel_project_for_user(db, project_id, current_user)
    refusal = archive_refusal(project.current_phase, project.phase_status)
    if refusal is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_REFUSAL_DETAIL[refusal],
        )
    if project.archived_at is None:
        project.archived_at = utc_now()
        await db.commit()
    return CarouselArchiveResponse(
        id=str(project.id), archived=True, archived_at=_aware(project.archived_at)
    )


@router.post(
    "/{project_id}/restore",
    response_model=CarouselArchiveResponse,
    summary="Restore an archived carousel to the board",
    responses=_RESPONSES,
)
async def restore_carousel(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> CarouselArchiveResponse:
    """Restore the carousel; the restore counts as activity for the auto-archive."""
    project = await get_carousel_project_for_user(db, project_id, current_user)
    if project.archived_at is not None:
        project.archived_at = None
        project.updated_at = utc_now()
        await db.commit()
    return CarouselArchiveResponse(id=str(project.id), archived=False)
