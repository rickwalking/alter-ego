"""Owner/admin routes for managed carousel creator branding assets.

Thin HTTP adapters (AE-0120). Each endpoint access-checks the request at the edge
(``assert_domain_owner_or_admin``), reads/validates the upload, then delegates the
upload/select use case to the presentation :class:`PresentationHandlers` (via the
presentation facade), and maps the result to the response. The routes no longer
construct the creator-asset service or the carousel repository directly and never
resolve the global container.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.carousel_creator_asset import (
    CreatorAssetResponse,
    CreatorAssetSelectRequest,
)
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetSelectCommand,
    CreatorAssetService,
    CreatorAssetUploadCommand,
)
from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetValidationError,
)
from rag_backend.domain.constants.creator_asset import (
    CREATOR_ASSET_MAX_BYTES,
    ERR_CREATOR_ASSET_FORBIDDEN,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject, User
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)
from rag_backend.modules.presentation import PresentationHandlers

router = APIRouter()


def get_creator_asset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatorAssetService:
    """Build the request-scoped creator-asset service (legacy edge construction).

    Kept here so the grandfathered ``creator_assets -> creator_asset_repository``
    import pair stays under this module; the AE-0120 presentation edge provider
    reuses this factory (imported lazily there to avoid an import cycle) so the
    creator-asset upload/select path is wired byte-identically behind the
    presentation handlers.
    """
    settings = get_settings()
    return CreatorAssetService(
        asset_repo=PostgresCreatorAssetRepository(session),
        carousel_repo=PostgresCarouselRepository(session),
        assets_root=Path(settings.carousel_creator_assets_dir),
    )


@dataclass(frozen=True)
class _CreatorAssetContext:
    user: User
    handlers: PresentationHandlers


def get_creator_asset_context(
    user: Annotated[User, Depends(require_authenticated_user)],
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> _CreatorAssetContext:
    return _CreatorAssetContext(user=user, handlers=handlers)


def _normalize_upload_mime(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _to_creator_asset_response(asset: CarouselCreatorAsset) -> CreatorAssetResponse:
    return CreatorAssetResponse(
        id=asset.id,
        owner_id=asset.owner_id,
        content_sha256=asset.content_sha256,
        media_type=asset.media_type,
        width=asset.width,
        height=asset.height,
        relative_path=asset.relative_path,
        staged_relative_path=asset.relative_path,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _map_validation_error(error: CreatorAssetValidationError) -> HTTPException:
    if error.code == ERR_CREATOR_ASSET_FORBIDDEN:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.code)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.code)


async def _load_owned_project(
    ctx: _CreatorAssetContext,
    project_id: UUID,
) -> CarouselProject:
    project = await ctx.handlers.get_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_CAROUSEL_NOT_FOUND
        )
    assert_domain_owner_or_admin(project.owner_id, ctx.user)
    return project


@router.post(
    "/{project_id}/creator-asset/upload",
    response_model=CreatorAssetResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_CAROUSEL_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def upload_creator_asset(
    request: Request,
    file: UploadFile,
    ctx: Annotated[_CreatorAssetContext, Depends(get_creator_asset_context)],
) -> CreatorAssetResponse:
    """Upload and bind a managed creator branding asset to a carousel project."""
    project_id = UUID(request.path_params["project_id"])
    project = await _load_owned_project(ctx, project_id)

    raw_bytes = await file.read()
    if len(raw_bytes) > CREATOR_ASSET_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="creator_asset_too_large",
        )

    try:
        result = await ctx.handlers.upload_creator_asset(
            CreatorAssetUploadCommand(
                project=project,
                user=ctx.user,
                content=raw_bytes,
                declared_mime=_normalize_upload_mime(file.content_type),
            )
        )
    except CreatorAssetValidationError as error:
        raise _map_validation_error(error) from error

    return _to_creator_asset_response(result.asset)


@router.put(
    "/{project_id}/creator-asset",
    response_model=CreatorAssetResponse,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_CAROUSEL_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def select_creator_asset(
    http_request: Request,
    request: CreatorAssetSelectRequest,
    ctx: Annotated[_CreatorAssetContext, Depends(get_creator_asset_context)],
) -> CreatorAssetResponse:
    """Select an existing managed creator asset for a carousel project."""
    project_id = UUID(http_request.path_params["project_id"])
    project = await _load_owned_project(ctx, project_id)

    try:
        result = await ctx.handlers.select_creator_asset(
            CreatorAssetSelectCommand(
                project=project,
                user=ctx.user,
                creator_asset_id=request.creator_asset_id,
            )
        )
    except CreatorAssetValidationError as error:
        raise _map_validation_error(error) from error

    return _to_creator_asset_response(result.asset)
