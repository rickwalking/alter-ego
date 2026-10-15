"""The owner's photo library and the POV slide-1 photo (AE-0376, ADR-0021 D8).

Mounted before the CRUD router so ``/creator-assets`` is never read as a
``/{project_id}``. Reuses the creator-asset service factory and the owner
checks of ``creator_assets.py`` (no new infrastructure import here).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

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

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.carousel_creator_asset import (
    CreatorAssetListResponse,
    CreatorAssetResponse,
    CreatorAssetSelectRequest,
    HookPhotoResponse,
)
from rag_backend.application.services.carousel.creator_asset_service import (
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
    ERR_CREATOR_ASSET_TOO_LARGE,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import User

from .creator_assets import (
    CreatorAssetContext,
    default_output_root,
    get_creator_asset_context,
    get_creator_asset_service,
    load_owned_project,
    map_validation_error,
    normalize_upload_mime,
    to_creator_asset_response,
)

router = APIRouter()

_LIBRARY_PATH = "/creator-assets"
_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"description": ERR_NOT_AUTHENTICATED},
    403: {"description": ERR_FORBIDDEN},
}


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
    file: UploadFile,
    role: Annotated[str, Form(pattern=CREATOR_ASSET_ROLE_PATTERN)],
    context: Annotated[CreatorAssetContext, Depends(get_creator_asset_context)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
    pose_tag: Annotated[
        str | None, Form(max_length=CREATOR_ASSET_POSE_TAG_MAX_CHARS)
    ] = None,
) -> CreatorAssetResponse:
    """Add a photo (PNG/WebP keep transparency, <=5 MB) to the caller's library."""
    del request
    raw_bytes = await file.read()
    if len(raw_bytes) > CREATOR_ASSET_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=ERR_CREATOR_ASSET_TOO_LARGE,
        )
    try:
        asset = await service.upload_to_library(
            LibraryUploadCommand(
                user=context.user,
                content=raw_bytes,
                declared_mime=normalize_upload_mime(file.content_type),
                role=role,
                pose_tag=(pose_tag or "").strip() or None,
            )
        )
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error
    return to_creator_asset_response(asset)


@router.get(f"{_LIBRARY_PATH}/{{asset_id}}/image", responses=_RESPONSES)
async def creator_asset_image(
    asset_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
) -> FileResponse:
    """One of the caller's photos (owner or admin only)."""
    try:
        path = await service.library_image_path(user, asset_id)
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error
    return FileResponse(path, media_type=CREATOR_ASSET_MEDIA_TYPE_WEBP)


@router.put(
    "/{project_id}/hook-photo",
    responses={**_RESPONSES, 404: {"description": ERR_CAROUSEL_NOT_FOUND}},
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def select_hook_photo(
    request: Request,
    body: CreatorAssetSelectRequest,
    context: Annotated[CreatorAssetContext, Depends(get_creator_asset_context)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
) -> HookPhotoResponse:
    """Use one of the owner's photos on slide 1 of a POV carousel."""
    project = await load_owned_project(context, UUID(request.path_params["project_id"]))
    try:
        updated = await service.select_hook_photo(
            HookPhotoCommand(
                project=project,
                user=context.user,
                creator_asset_id=body.creator_asset_id,
                output_root=default_output_root(project),
            )
        )
    except CreatorAssetValidationError as error:
        raise map_validation_error(error) from error
    return HookPhotoResponse(project_id=updated.id, hook_asset_id=body.creator_asset_id)


__all__ = ["router"]
