"""The owner's photo library and the POV slide-1 photo (ADR-0021 D8).

Mounted before the CRUD router so ``/creator-assets`` is never read as a
``/{project_id}``. Reuses the creator-asset service factory and the owner
checks of ``creator_assets.py`` (no new infrastructure import here).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.carousel_creator_asset import (
    CreatorAssetInUseDetail,
    CreatorAssetInUseResponse,
    CreatorAssetListResponse,
    CreatorAssetResponse,
    CreatorAssetSelectRequest,
    CreatorAssetTopicUsageResponse,
    CreatorAssetUsageResponse,
    HookPhotoResponse,
)
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetInUseError,
    CreatorAssetService,
    HookPhotoCommand,
    LibraryUploadCommand,
)
from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetValidationError,
)
from rag_backend.domain.constants.creator_asset import (
    CREATOR_ASSET_MAX_BYTES,
    CREATOR_ASSET_MEDIA_TYPE_WEBP,
    CREATOR_ASSET_POSE_TAG_MAX_CHARS,
    CREATOR_ASSET_ROLE_PATTERN,
    ERR_CREATOR_ASSET_COVER_MANAGED,
    ERR_CREATOR_ASSET_IN_USE,
    ERR_CREATOR_ASSET_NOT_FOUND,
    ERR_CREATOR_ASSET_TOO_LARGE,
    LOG_STALE_PHOTO_UNLINK_FAILED,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import User

from .creator_assets import (
    CreatorAssetContext,
    default_output_root,
    get_creator_asset_context,
    get_creator_asset_service,
    get_creator_asset_session,
    load_owned_project,
    map_validation_error,
    normalize_upload_mime,
    to_creator_asset_response,
)

router = APIRouter()
logger = structlog.get_logger(__name__)

_LIBRARY_PATH = "/creator-assets"
_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"description": ERR_NOT_AUTHENTICATED},
    403: {"description": ERR_FORBIDDEN},
}


@dataclass(frozen=True)
class _Library:
    """The caller's context, the creator-asset service and its request session."""

    context: CreatorAssetContext
    service: CreatorAssetService
    session: AsyncSession


def _library(
    context: Annotated[CreatorAssetContext, Depends(get_creator_asset_context)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
    session: Annotated[AsyncSession, Depends(get_creator_asset_session)],
) -> _Library:
    return _Library(context=context, service=service, session=session)


@dataclass(frozen=True)
class _PhotoForm:
    """The multipart upload: the image, its role and an optional pose tag."""

    file: UploadFile
    role: str
    pose_tag: str | None


def _photo_form(
    file: UploadFile,
    role: Annotated[str, Form(pattern=CREATOR_ASSET_ROLE_PATTERN)],
    pose_tag: Annotated[
        str | None, Form(max_length=CREATOR_ASSET_POSE_TAG_MAX_CHARS)
    ] = None,
) -> _PhotoForm:
    return _PhotoForm(file=file, role=role, pose_tag=(pose_tag or "").strip() or None)


def _library_error(error: CreatorAssetValidationError) -> HTTPException:
    """404 unknown, 409 in use (with its users) or a GrokBot cover, else shared."""
    if isinstance(error, CreatorAssetInUseError):
        detail = CreatorAssetInUseDetail(
            code=error.code,
            carousels=[
                CreatorAssetUsageResponse(id=usage.project_id, title=usage.title)
                for usage in error.usages
            ],
            topics=[
                CreatorAssetTopicUsageResponse(id=topic.topic_id, title=topic.title)
                for topic in error.topics
            ],
        )
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail.model_dump(mode="json"),
        )
    if error.code == ERR_CREATOR_ASSET_COVER_MANAGED:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.code)
    if error.code == ERR_CREATOR_ASSET_NOT_FOUND:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.code)
    return map_validation_error(error)


@router.get(_LIBRARY_PATH, responses=_RESPONSES)
async def list_creator_assets(
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
    role: Annotated[str | None, Query(pattern=CREATOR_ASSET_ROLE_PATTERN)] = None,
) -> CreatorAssetListResponse:
    """The caller's own photos, newest first, optionally by role."""
    assets = await service.list_library(user, role)
    return CreatorAssetListResponse(
        items=[to_creator_asset_response(asset) for asset in assets]
    )


@router.post(_LIBRARY_PATH, status_code=status.HTTP_201_CREATED, responses=_RESPONSES)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def upload_library_photo(
    request: Request,
    form: Annotated[_PhotoForm, Depends(_photo_form)],
    library: Annotated[_Library, Depends(_library)],
) -> CreatorAssetResponse:
    """Add a photo (PNG/WebP keep transparency, <=5 MB) to the caller's library."""
    del request
    raw_bytes = await form.file.read()
    if len(raw_bytes) > CREATOR_ASSET_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=ERR_CREATOR_ASSET_TOO_LARGE,
        )
    try:
        asset = await library.service.upload_to_library(
            LibraryUploadCommand(
                user=library.context.user,
                content=raw_bytes,
                declared_mime=normalize_upload_mime(form.file.content_type),
                role=form.role,
                pose_tag=form.pose_tag,
            )
        )
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error
    return to_creator_asset_response(asset)


@router.get(
    f"{_LIBRARY_PATH}/{{asset_id}}/image",
    responses={**_RESPONSES, 404: {"description": ERR_CREATOR_ASSET_NOT_FOUND}},
)
async def creator_asset_image(
    asset_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
) -> FileResponse:
    """One of the caller's photos (owner or admin only); 404 once it is gone."""
    try:
        path = await service.library_image_path(user, asset_id)
    except CreatorAssetValidationError as error:
        raise _library_error(error) from error
    return FileResponse(path, media_type=CREATOR_ASSET_MEDIA_TYPE_WEBP)


@router.delete(
    f"{_LIBRARY_PATH}/{{asset_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **_RESPONSES,
        404: {"description": ERR_CREATOR_ASSET_NOT_FOUND},
        409: {
            "description": ERR_CREATOR_ASSET_IN_USE,
            "model": CreatorAssetInUseResponse,
        },
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def delete_library_photo(
    request: Request,
    asset_id: UUID,
    library: Annotated[_Library, Depends(_library)],
) -> None:
    """Delete one of the owner's photos and its file; 409 while a carousel uses it."""
    del request
    try:
        stale = await library.service.delete_library_photo(
            library.context.user, asset_id
        )
    except CreatorAssetValidationError as error:
        raise _library_error(error) from error
    await library.session.commit()
    if stale is None:
        return
    try:
        stale.unlink(missing_ok=True)
    except OSError:
        logger.warning(LOG_STALE_PHOTO_UNLINK_FAILED, asset_id=str(asset_id))


@router.put(
    "/{project_id}/hook-photo",
    responses={**_RESPONSES, 404: {"description": ERR_CAROUSEL_NOT_FOUND}},
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def select_hook_photo(
    request: Request,
    body: CreatorAssetSelectRequest,
    library: Annotated[_Library, Depends(_library)],
) -> HookPhotoResponse:
    """Use one of the owner's photos on slide 1 of a POV carousel."""
    project_id = UUID(request.path_params["project_id"])
    project = await load_owned_project(library.context, project_id)
    try:
        updated = await library.service.select_hook_photo(
            HookPhotoCommand(
                project=project,
                user=library.context.user,
                creator_asset_id=body.creator_asset_id,
                output_root=default_output_root(project),
            )
        )
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error
    return HookPhotoResponse(project_id=updated.id, hook_asset_id=body.creator_asset_id)


__all__ = ["router"]
