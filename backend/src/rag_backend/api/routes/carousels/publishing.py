from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
)
from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    CarouselCaptionResponse,
    InstagramPublishRequest,
    InstagramPublishResponse,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_CAROUSEL_NOT_COMPLETED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
    RATE_LIMIT_CAROUSEL_PUBLISH,
)
from rag_backend.domain.models import CarouselStatus, User
from rag_backend.domain.protocols import (
    CarouselRepository,
    SocialPublisher,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel

from .deps import get_carousel_repo, get_instagram_publisher
from .helpers import _build_public_image_urls, assert_carousel_artifacts_healthy

router = APIRouter()


@router.post(
    "/{project_id}/caption",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def generate_caption(
    request: Request,
    project_id: UUID,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselCaptionResponse:
    """Return caption from project state; does not run legacy pipeline."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_domain_owner_or_admin(project.owner_id, user)
    return CarouselCaptionResponse(
        caption=project.caption or "",
        hashtags=[],
    )


@router.post(
    "/{project_id}/publish/instagram",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
        409: {"description": "Carousel not completed"},
        503: {"description": "Public base URL not configured"},
    },
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def publish_to_instagram(
    request: Request,
    project_id: UUID,
    body: InstagramPublishRequest,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    publisher: Annotated[SocialPublisher, Depends(get_instagram_publisher)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstagramPublishResponse:
    """Publish the carousel's slides to Instagram with the provided caption."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    assert_domain_owner_or_admin(project.owner_id, user)
    model = await db.get(CarouselProjectModel, str(project_id))
    if model is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if model.workflow_status != WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        raise HTTPException(
            status_code=403,
            detail=ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
        )
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=ERR_CAROUSEL_NOT_COMPLETED,
        )
    slides = await repo.get_slides_by_project(project_id)
    assert_carousel_artifacts_healthy(project, slides)
    slide_numbers = [slide.slide_number for slide in slides]

    try:
        image_urls = _build_public_image_urls(project_id, slide_numbers)
    except RuntimeError as exc:
        if str(exc) == ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED:
            raise HTTPException(
                status_code=503,
                detail=ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED,
            ) from None
        raise HTTPException(
            status_code=503,
            detail=ERR_INSTAGRAM_PUBLIC_BASE_URL_NOT_CONFIGURED,
        ) from None

    result = await publisher.publish_instagram(body.caption, image_urls)
    return InstagramPublishResponse(
        status=result.status,
        ig_post_id=result.post_id,
        error_message=result.error_message,
    )
