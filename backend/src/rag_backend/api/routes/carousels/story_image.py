"""Public Story image route (AE-0369).

Meta's fetcher GETs this JPEG when the autopilot posts the Story that
announces a carousel. Same gate as ``slide-images``: served only while the
carousel is public, 404 otherwise.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from rag_backend.api.constants import (
    CAROUSEL_CACHE_HEADERS,
    ERR_CAROUSEL_NOT_FOUND,
    ERR_IMAGE_NOT_FOUND,
    ERR_NOT_FOUND,
    MEDIA_TYPE_JPEG,
)
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.modules.presentation import PresentationHandlers
from rag_backend.modules.publishing import story_image_file

from .carousel_access import assert_carousel_public

router = APIRouter()

STORY_IMAGE_PATH = "/{project_id}/story-image/pt.jpg"


@router.get(STORY_IMAGE_PATH, responses={404: {"description": ERR_NOT_FOUND}})
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def get_carousel_story_image(
    request: Request,
    project_id: UUID,
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> FileResponse:
    """Serve the rendered ``story_pt.jpg`` of a public carousel."""
    project = await handlers.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_carousel_public(project)
    story = story_image_file(project.output_dir, project.artifact_version)
    if story is None:
        raise HTTPException(status_code=404, detail=ERR_IMAGE_NOT_FOUND)
    return FileResponse(
        path=str(story),
        media_type=MEDIA_TYPE_JPEG,
        headers=CAROUSEL_CACHE_HEADERS,
    )
