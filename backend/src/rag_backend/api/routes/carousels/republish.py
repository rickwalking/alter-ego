"""Carousel artifact republish route (AE-0313).

Thin HTTP adapter: authenticate (owner or assigned reviewer), gate on
``completed`` status + a non-active workflow run, then run the full finalize
pipeline under the shared per-project build lock. A failed republish never
corrupts the completed project — it stays on its prior artifact version and the
error is returned to the caller (the finalize pipeline preserves completed
projects; AE-0313).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_workflow_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.carousel import CarouselRepublishResponse
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.application.services.carousel.artifact_health import (
    format_artifact_health_errors,
)
from rag_backend.application.services.carousel.carousel_republish import (
    republish_completed_carousel,
)
from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_BUILD_IN_PROGRESS,
    CONFLICT_CODE_RUN_IN_PROGRESS,
)
from rag_backend.domain.constants.carousel_republish import (
    ERR_REPUBLISH_NOT_COMPLETED,
    REPUBLISH_STATUS_REPUBLISHED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

router = APIRouter(tags=["carousels-republish"])


def _reject_if_run_active(phase_status: str) -> None:
    """A completed carousel with an active run must not be republished.

    Pins the ``completed`` ↔ ``phase_status`` invariant: republish and a
    workflow resume can never mutate the project concurrently.
    """
    if phase_status == PHASE_STATUS_IN_PROGRESS:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        )


def _raise_republish_failure(errors: tuple[str, ...]) -> None:
    """Map a preserved-project finalize failure onto the right HTTP status."""
    if ERR_ARTIFACT_BUILD_CONFLICT in errors:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_BUILD_IN_PROGRESS)
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=format_artifact_health_errors(errors),
    )


@router.post(
    "/{project_id}/republish",
    response_model=CarouselRepublishResponse,
    summary="Rebuild and re-activate a completed carousel's artifacts",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Typed conflict: a workflow run or another artifact build is "
                "in progress for this carousel (AE-0313/AE-0316)."
            ),
            "model": CarouselConflictResponse,
        },
    },
)
async def republish_carousel(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> CarouselRepublishResponse:
    """Re-render from persisted slides and activate a fresh artifact version."""
    project = await get_carousel_project_for_workflow_user(db, project_id, current_user)
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_REPUBLISH_NOT_COMPLETED,
        )
    _reject_if_run_active(project.phase_status)

    result = await republish_completed_carousel(db, str(project_id))
    if not result.completed:
        _raise_republish_failure(result.errors)

    # The finalize pipeline persists + refreshes the SAME session-identity
    # project row (repo.update_project), so its artifact_version / PDF pointers
    # are already current — no ORM re-fetch (which would add a forbidden
    # api -> infrastructure edge) is needed.
    return CarouselRepublishResponse(
        project_id=str(project_id),
        status=REPUBLISH_STATUS_REPUBLISHED,
        artifact_version=project.artifact_version,
        pdf_path=project.pdf_path,
        pdf_path_en=project.pdf_path_en,
    )


__all__ = ["router"]
