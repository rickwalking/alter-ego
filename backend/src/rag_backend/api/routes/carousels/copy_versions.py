"""Version history of a carousel's Instagram caption and LinkedIn posts.

Owner or admin only. ``GET`` lists the versions newest first; ``POST .../restore``
saves a version's text through the copy save (``If-Match`` lock version, the
run guard and the read-only published caption), which records it as a new
version.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.dependencies.blog_content_write import require_if_match
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.routes.carousels.copy_edit import (
    copy_response,
    reject_published_caption,
)
from rag_backend.api.routes.carousels.deps import (
    CarouselCopyEditRouteDeps,
    get_carousel_copy_edit_route_deps,
)
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_copy import (
    CarouselCopyResponse,
    CarouselCopyVersionResponse,
    CarouselCopyVersionsResponse,
)
from rag_backend.application.services.carousel.carousel_copy_edit_service import (
    CopyEditCommand,
    CopyEdits,
)
from rag_backend.domain.constants.carousel_copy_versions import (
    ERR_COPY_VERSION_NOT_FOUND,
)
from rag_backend.domain.constants.distribution import (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_KEYS,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_copy_version import CopyVersion

router = APIRouter(tags=["carousels-copy"])

CopyDeps = Annotated[
    CarouselCopyEditRouteDeps, Depends(get_carousel_copy_edit_route_deps)
]


async def _owned_project(
    deps: CarouselCopyEditRouteDeps, project_id: UUID
) -> CarouselProject:
    """The carousel, 404 when missing and 403 unless owner or admin."""
    project = await deps.repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_domain_owner_or_admin(project.owner_id, deps.user)
    return project


def _edits_for(version: CopyVersion) -> CopyEdits:
    """The save that puts ``version``'s text back into its field."""
    texts = {
        DISTRIBUTION_CAPTION_KEY: None,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: None,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: None,
    }
    texts[version.field] = version.text
    return CopyEdits(
        caption=texts[DISTRIBUTION_CAPTION_KEY],
        linkedin_post_pt=texts[DISTRIBUTION_LINKEDIN_POST_PT_KEY],
        linkedin_post_en=texts[DISTRIBUTION_LINKEDIN_POST_EN_KEY],
    )


@router.get(
    "/{project_id}/copy/versions",
    response_model=CarouselCopyVersionsResponse,
    summary="List the caption and LinkedIn post versions of a carousel",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not the owner or an admin"},
        status.HTTP_404_NOT_FOUND: {"description": ERR_CAROUSEL_NOT_FOUND},
    },
)
async def list_carousel_copy_versions(
    project_id: UUID, deps: CopyDeps
) -> CarouselCopyVersionsResponse:
    """Every stored version, newest first, with who saved it and when."""
    await _owned_project(deps, project_id)
    versions = await deps.service.versions(str(project_id))
    return CarouselCopyVersionsResponse(
        project_id=project_id,
        versions=[
            CarouselCopyVersionResponse.model_validate(v, from_attributes=True)
            for v in versions
        ],
    )


@router.post(
    "/{project_id}/copy/versions/{version_number}/restore",
    response_model=CarouselCopyResponse,
    summary="Restore a caption or LinkedIn post version of a carousel",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not the owner or an admin"},
        status.HTTP_404_NOT_FOUND: {"description": "Carousel or version not found"},
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
async def restore_carousel_copy_version(
    project_id: UUID, version_number: int, deps: CopyDeps
) -> CarouselCopyResponse:
    """Save the version's text; the restore is recorded as a new version.

    A version that names no caption / LinkedIn field is not restorable (404).
    """
    project = await _owned_project(deps, project_id)
    lock_version = require_if_match(deps.if_match)
    version = await deps.service.version(str(project_id), version_number)
    if version is None or version.field not in DISTRIBUTION_KEYS:
        raise HTTPException(status_code=404, detail=ERR_COPY_VERSION_NOT_FOUND)
    if version.field == DISTRIBUTION_CAPTION_KEY:
        await reject_published_caption(deps, project_id)
    result = await deps.service.save(
        CopyEditCommand(
            project=project,
            lock_version=lock_version,
            edits=_edits_for(version),
            author_id=str(deps.user.id),
            restored_from=version_number,
        )
    )
    return copy_response(project_id, result)


__all__ = ["router"]
