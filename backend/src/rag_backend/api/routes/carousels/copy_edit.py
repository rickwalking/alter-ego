"""Save the Instagram caption and LinkedIn posts of a carousel.

Thin HTTP adapter: owner or admin only, ``If-Match`` required (the carousel
``lock_version`` the page loaded), and the caption of a carousel already
published on Instagram is read-only. The service takes the ``lock_version``
compare-and-swap and writes through the carousel repository; its typed 409
conflicts (``resume_already_in_progress``, ``version_conflict``) go through the
app-wide carousel-conflict handler.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.dependencies.blog_content_write import require_if_match
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.routes.carousels.deps import (
    CarouselCopyEditRouteDeps,
    get_carousel_copy_edit_route_deps,
)
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_copy import (
    CarouselCopyResponse,
    CarouselCopyUpdateRequest,
)
from rag_backend.application.services.carousel.carousel_copy_edit_service import (
    CopyEditCommand,
    CopyEditResult,
    CopyEdits,
)
from rag_backend.domain.constants.carousel_copy_edit import ERR_CAPTION_PUBLISHED
from rag_backend.modules.autopilot import AutopilotBootstrapDeps, bootstrap_module

router = APIRouter(tags=["carousels-copy"])


async def reject_published_caption(
    deps: CarouselCopyEditRouteDeps, project_id: UUID
) -> None:
    """409 when the caption of a carousel already on Instagram is changed."""
    module = bootstrap_module(AutopilotBootstrapDeps(session=deps.db))
    view = await module.instagram_status(str(project_id))
    if view.ig_post_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_CAPTION_PUBLISHED
        )


@router.patch(
    "/{project_id}/copy",
    response_model=CarouselCopyResponse,
    summary="Save the Instagram caption and the LinkedIn posts of a carousel",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not the owner or an admin"},
        status.HTTP_404_NOT_FOUND: {"description": ERR_CAROUSEL_NOT_FOUND},
        status.HTTP_409_CONFLICT: {
            "description": (
                "A workflow run is active, the lock version is stale, or the "
                "caption is already published on Instagram."
            ),
            "model": CarouselConflictResponse,
        },
        status.HTTP_428_PRECONDITION_REQUIRED: {"description": "If-Match missing"},
    },
)
async def save_carousel_copy(
    project_id: UUID,
    payload: CarouselCopyUpdateRequest,
    deps: Annotated[
        CarouselCopyEditRouteDeps, Depends(get_carousel_copy_edit_route_deps)
    ],
) -> CarouselCopyResponse:
    """Persist the edited texts; unsent texts keep their saved value."""
    project = await deps.repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_domain_owner_or_admin(project.owner_id, deps.user)
    lock_version = require_if_match(deps.if_match)
    if payload.caption is not None:
        await reject_published_caption(deps, project_id)
    result = await deps.service.save(
        CopyEditCommand(
            project=project,
            lock_version=lock_version,
            edits=CopyEdits(
                caption=payload.caption,
                linkedin_post_pt=payload.linkedin_post_pt,
                linkedin_post_en=payload.linkedin_post_en,
            ),
            author_id=str(deps.user.id),
        )
    )
    return copy_response(project_id, result)


def copy_response(project_id: UUID, result: CopyEditResult) -> CarouselCopyResponse:
    """The saved texts and the lock version the next save must send."""
    saved = result.project
    return CarouselCopyResponse(
        project_id=project_id,
        caption=saved.caption,
        linkedin_post_pt=saved.linkedin_post_pt,
        linkedin_post_en=saved.linkedin_post_en,
        lock_version=result.lock_version,
    )


__all__ = ["copy_response", "reject_published_caption", "router"]
