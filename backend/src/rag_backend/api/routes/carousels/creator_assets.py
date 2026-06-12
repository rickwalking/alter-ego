"""Owner/admin routes for managed carousel creator branding assets."""

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
from rag_backend.domain.models import User
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)

from .deps import get_carousel_repo

router = APIRouter()


@dataclass(frozen=True)
class _CreatorAssetContext:
    user: User
    repo: CarouselRepository
    service: CreatorAssetService


def get_creator_asset_context(
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    service: Annotated[CreatorAssetService, Depends(get_creator_asset_service)],
) -> _CreatorAssetContext:
    return _CreatorAssetContext(user=user, repo=repo, service=service)


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


def get_creator_asset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreatorAssetService:
    settings = get_settings()
    return CreatorAssetService(
        asset_repo=PostgresCreatorAssetRepository(session),
        carousel_repo=PostgresCarouselRepository(session),
        assets_root=Path(settings.carousel_creator_assets_dir),
    )


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
    project = await ctx.repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_CAROUSEL_NOT_FOUND
        )
    assert_domain_owner_or_admin(project.owner_id, ctx.user)

    raw_bytes = await file.read()
    if len(raw_bytes) > CREATOR_ASSET_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="creator_asset_too_large",
        )

    try:
        asset, _ = await ctx.service.upload_for_project(
            CreatorAssetUploadCommand(
                project=project,
                user=ctx.user,
                content=raw_bytes,
                declared_mime=_normalize_upload_mime(file.content_type),
            )
        )
    except CreatorAssetValidationError as error:
        raise _map_validation_error(error) from error

    return _to_creator_asset_response(asset)


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
    project = await ctx.repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_CAROUSEL_NOT_FOUND
        )
    assert_domain_owner_or_admin(project.owner_id, ctx.user)

    try:
        asset, _ = await ctx.service.select_for_project(
            CreatorAssetSelectCommand(
                project=project,
                user=ctx.user,
                creator_asset_id=request.creator_asset_id,
            )
        )
    except CreatorAssetValidationError as error:
        raise _map_validation_error(error) from error

    return _to_creator_asset_response(asset)
