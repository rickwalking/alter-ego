from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
)
from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.schemas import (
    CarouselCaptionResponse,
    InstagramPublishRequest,
    InstagramPublishResponse,
)
from rag_backend.domain.models import CarouselStatus, User
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository, SocialPublisher

from .deps import get_carousel_agent, get_carousel_repo, get_instagram_publisher
from .helpers import _build_public_image_urls

router = APIRouter()


@router.post(
    "/{project_id}/caption",
    responses={
         401: {"description": ERR_NOT_AUTHENTICATED},
         403: {"description": ERR_FORBIDDEN},
         404: {"description": ERR_NOT_FOUND},
    },
)
async def generate_caption(
    project_id: UUID,
    user: Annotated[User, Depends(require_editor_or_admin)],
    agent: Annotated[CarouselAgent, Depends(get_carousel_agent)],
) -> CarouselCaptionResponse:
    """Generate Instagram caption for a carousel."""
    project = await agent.execute_pipeline(project_id)
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
async def publish_to_instagram(
    project_id: UUID,
    body: InstagramPublishRequest,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    publisher: Annotated[SocialPublisher, Depends(get_instagram_publisher)],
) -> InstagramPublishResponse:
    """Publish the carousel's slides to Instagram with the provided caption."""
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Carousel is in status {project.status.value}; must be completed.",
        )

    try:
        image_urls = _build_public_image_urls(project_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = await publisher.publish_instagram(body.caption, image_urls)
    return InstagramPublishResponse(
        status=result.status,
        ig_post_id=result.post_id,
        error_message=result.error_message,
    )
