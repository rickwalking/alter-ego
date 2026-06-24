"""Custom-palette catalog CRUD API (AE-0270).

Exposes ``GET/POST/PATCH/DELETE /palettes`` behind the ``palette_catalog`` feature
flag (OFF in prod until the AE-0271 frontend ships — skeptical G6). Roots are
read-only (403); custom palettes are editable by any authenticated user (D7);
delete is a soft archive (D4). Request-shape security (strict hex, name XSS,
keyword guards) lives in the Pydantic schema; this module owns auth, the feature
gate, rate-limiting, and the ``IntegrityError`` -> 409 mapping for the concurrent
duplicate-name race (skeptical F3). ``get_palette_repo`` is the single reviewed
``api -> infrastructure`` edge (baseline 76 -> 77).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
)
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequirePaletteCatalog
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.palette import (
    CustomPaletteResponse,
    PaletteCatalogResponse,
    PaletteCreateRequest,
    PaletteUpdateRequest,
    RootPaletteResponse,
)
from rag_backend.application.services.carousel.palette_catalog_service import (
    PaletteCatalogService,
    PaletteCreateCommand,
    PaletteNotFoundError,
    PaletteUpdateCommand,
    is_root_key,
)
from rag_backend.domain.constants.carousel_themes import PALETTE_REGISTRY
from rag_backend.domain.constants.palette_catalog import (
    ERR_PALETTE_NAME_CONFLICT,
    ERR_PALETTE_NOT_FOUND,
    ERR_ROOT_PALETTE_IMMUTABLE,
)
from rag_backend.domain.constants.palette_types import PaletteKind
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_PALETTE_WRITE
from rag_backend.domain.models import User
from rag_backend.domain.models.palette import CustomPalette
from rag_backend.domain.protocols.palette import PaletteRepository
from rag_backend.infrastructure.database.palette_repository import (
    PostgresPaletteRepository,
)

router = APIRouter(
    prefix="/palettes",
    tags=["palettes"],
    dependencies=[RequirePaletteCatalog],
)


def get_palette_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaletteRepository:
    """Build the request-scoped custom-palette repository (the api->infra edge)."""
    return PostgresPaletteRepository(session)


def get_palette_service(
    repo: Annotated[PaletteRepository, Depends(get_palette_repo)],
) -> PaletteCatalogService:
    """Build the catalog service over the request-scoped repository port."""
    return PaletteCatalogService(repo)


@dataclass(frozen=True)
class PaletteWriteCtx:
    """Bundled per-request collaborators for the authenticated write endpoints.

    Grouping auth + service + session into one dependency keeps each route handler
    within the 3-argument limit while still resolving them via FastAPI DI.
    """

    user: User
    service: PaletteCatalogService
    session: AsyncSession


def get_palette_write_ctx(
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[PaletteCatalogService, Depends(get_palette_service)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaletteWriteCtx:
    """Resolve the authenticated write context (auth enforced by the dependency)."""
    return PaletteWriteCtx(user=user, service=service, session=session)


@dataclass(frozen=True)
class PaletteEditTarget:
    """A resolved custom-palette edit target: its id plus the write context."""

    palette_id: UUID
    ctx: PaletteWriteCtx


def get_palette_edit_target(
    ref: str,
    ctx: Annotated[PaletteWriteCtx, Depends(get_palette_write_ctx)],
) -> PaletteEditTarget:
    """Resolve ``{ref}`` to a custom-palette id (root -> 403; non-uuid -> 404)."""
    return PaletteEditTarget(palette_id=_as_custom_id(ref), ctx=ctx)


def _root_rows() -> list[RootPaletteResponse]:
    """Project the user-selectable (non-brand) root palettes from the registry."""
    return [
        RootPaletteResponse(
            key=descriptor.key,
            label_en=descriptor.label_en,
            label_pt=descriptor.label_pt,
            mode=descriptor.mode.value,
            primary=descriptor.palette.primary,
            accent=descriptor.palette.accent,
            background=descriptor.palette.background,
        )
        for descriptor in PALETTE_REGISTRY
        if descriptor.kind is not PaletteKind.BRAND
    ]


def _to_response(palette: CustomPalette) -> CustomPaletteResponse:
    """Map a ``CustomPalette`` entity to its API response."""
    return CustomPaletteResponse(
        id=palette.id,
        name=palette.name,
        slug=palette.slug,
        primary=palette.palette.primary,
        accent=palette.palette.accent,
        background=palette.palette.background,
        mode=palette.mode.value,
        keywords=list(palette.keywords),
        archived=palette.archived,
        created_by=palette.created_by,
        created_at=palette.created_at,
        updated_at=palette.updated_at,
    )


def _reject_root(ref: str) -> None:
    """403 if ``ref`` names a read-only root palette (write paths only)."""
    if is_root_key(ref):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ROOT_PALETTE_IMMUTABLE,
        )


def _as_custom_id(ref: str) -> UUID:
    """Parse ``ref`` to a custom-palette UUID, or 404 if it is not one."""
    _reject_root(ref)
    try:
        return UUID(ref)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PALETTE_NOT_FOUND
        ) from exc


@router.get("", responses={401: {"description": ERR_NOT_AUTHENTICATED}})
async def list_palettes(
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[PaletteCatalogService, Depends(get_palette_service)],
) -> PaletteCatalogResponse:
    """Return the catalog: read-only roots + active custom palettes (D1)."""
    customs = await service.list_active()
    return PaletteCatalogResponse(
        roots=_root_rows(),
        custom=[_to_response(palette) for palette in customs],
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        409: {"description": ERR_PALETTE_NAME_CONFLICT},
    },
)
@limiter.limit(RATE_LIMIT_PALETTE_WRITE)
async def create_palette(
    request: Request,
    body: PaletteCreateRequest,
    ctx: Annotated[PaletteWriteCtx, Depends(get_palette_write_ctx)],
) -> CustomPaletteResponse:
    """Create a custom palette; concurrent duplicate active name -> 409 (F3)."""
    command = PaletteCreateCommand(
        name=body.name,
        primary=body.primary,
        accent=body.accent,
        background=body.background,
        mode=body.mode,
        keywords=tuple(body.keywords),
        created_by=str(ctx.user.id),
    )
    try:
        created = await ctx.service.create(command)
        await ctx.session.commit()
    except IntegrityError as exc:
        await ctx.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_PALETTE_NAME_CONFLICT
        ) from exc
    return _to_response(created)


@router.patch(
    "/{ref}",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
        409: {"description": ERR_PALETTE_NAME_CONFLICT},
    },
)
@limiter.limit(RATE_LIMIT_PALETTE_WRITE)
async def update_palette(
    request: Request,
    body: PaletteUpdateRequest,
    target: Annotated[PaletteEditTarget, Depends(get_palette_edit_target)],
) -> CustomPaletteResponse:
    """Edit a custom palette. Roots -> 403; unknown/archived -> 404; slug is immutable."""
    command = PaletteUpdateCommand(
        name=body.name,
        primary=body.primary,
        accent=body.accent,
        background=body.background,
        mode=body.mode,
        keywords=None if body.keywords is None else tuple(body.keywords),
    )
    ctx = target.ctx
    try:
        updated = await ctx.service.update(target.palette_id, command)
        await ctx.session.commit()
    except PaletteNotFoundError as exc:
        await ctx.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PALETTE_NOT_FOUND
        ) from exc
    except IntegrityError as exc:
        await ctx.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_PALETTE_NAME_CONFLICT
        ) from exc
    return _to_response(updated)


@router.delete(
    "/{ref}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
@limiter.limit(RATE_LIMIT_PALETTE_WRITE)
async def delete_palette(
    request: Request,
    target: Annotated[PaletteEditTarget, Depends(get_palette_edit_target)],
) -> None:
    """Soft-delete (archive) a custom palette. Roots -> 403; unknown -> 404 (D4)."""
    ctx = target.ctx
    archived = await ctx.service.archive(target.palette_id)
    if not archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PALETTE_NOT_FOUND
        )
    await ctx.session.commit()
