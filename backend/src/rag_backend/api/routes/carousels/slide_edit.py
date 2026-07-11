"""Completed-project slide-text edit route (AE-0314).

Thin HTTP adapter: authenticate (owner or assigned reviewer), gate on
``completed`` status, sanitize the edited copy case-preservingly (AE-0289), then
apply the deterministic text edit under the shared per-project advisory lock via
``CarouselSlideEditService``. Images are never regenerated. The service stamps a
persisted ``needs_republish`` marker in the same transaction and converges the
checkpoint; typed 409 conflicts (``resume_already_in_progress`` while a run is
active, ``mutation_in_progress`` while another mutator holds the lock,
``version_conflict`` when a concurrent mutator wins the CAS) propagate to the
app-wide carousel-conflict handler (AE-0316).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_workflow_user,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.routes.carousels.deps import (
    CarouselSlideEditRouteDeps,
    get_carousel_slide_edit_route_deps,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_sanitize import (
    sanitize_edited_slides,
)
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_slide_edit import (
    CarouselSlideEditRequest,
    CarouselSlideEditResponse,
)
from rag_backend.application.services.carousel.carousel_slide_edit_service import (
    SlideEditCommand,
    SlideEditResult,
)
from rag_backend.domain.constants.carousel_slide_edit import (
    ERR_SLIDE_EDIT_NOT_COMPLETED,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.carousel_presentation import SlideValidationReport

router = APIRouter(tags=["carousels-slide-edit"])


def _to_response(project_id: str, result: SlideEditResult) -> CarouselSlideEditResponse:
    """Map the service result onto the API response (fresh report included)."""
    return CarouselSlideEditResponse(
        project_id=project_id,
        status=result.status,
        validation=SlideValidationReport.model_validate(result.report),
        needs_republish=result.needs_republish,
        updated_slides=list(result.updated_slides),
    )


@router.patch(
    "/{project_id}/slides",
    response_model=CarouselSlideEditResponse,
    summary="Edit a completed carousel's slide text without regenerating images",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Typed conflict: a workflow run is in progress, another mutator "
                "holds the project lock, or a concurrent mutator won the CAS "
                "(AE-0314/AE-0316)."
            ),
            "model": CarouselConflictResponse,
        },
    },
)
async def edit_carousel_slides(
    project_id: UUID,
    payload: CarouselSlideEditRequest,
    deps: Annotated[
        CarouselSlideEditRouteDeps, Depends(get_carousel_slide_edit_route_deps)
    ],
    current_user: EditorUser,
) -> CarouselSlideEditResponse:
    """Persist reviewer text edits + mark a republish; images stay unchanged."""
    project = await get_carousel_project_for_workflow_user(
        deps.db, project_id, current_user
    )
    if project.status != CarouselStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ERR_SLIDE_EDIT_NOT_COMPLETED,
        )
    command = SlideEditCommand(
        project_id=str(project_id),
        phase_status=str(project.phase_status or ""),
        lock_version=int(project.lock_version or 1),
        policy_version=project.presentation_policy_version,
        actor_user_id=str(current_user.id),
        edited_slides=sanitize_edited_slides(payload.edited_slides),
    )
    result = await deps.service.edit(command)
    return _to_response(str(project_id), result)


__all__ = ["router"]
