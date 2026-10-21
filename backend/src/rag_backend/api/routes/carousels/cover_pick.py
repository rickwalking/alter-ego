"""Publish-step slide-1 cover picker of a Ponto de Vista carousel (AE-0445).

Thin HTTP adapter. The project owner (or an admin) lists the images slide 1
may show (``GET /{id}/cover-options``: library photos, then the autopilot
run's GrokBot cover offer) and picks one (``PUT /{id}/cover``) at the
workflow lock version the page read. The pick is staged, stored under the
lock-version CAS and re-rendered through the AE-0313 republish path; typed
409s (stale version, held lock, active run, build in progress) go through the
app-wide carousel-conflict handler (AE-0316).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import assert_domain_owner_or_admin
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.carousels.republish import raise_republish_failure
from rag_backend.api.schemas.carousel_conflict import CarouselConflictResponse
from rag_backend.api.schemas.carousel_cover_pick import (
    CoverOptionResponse,
    CoverOptionsResponse,
    CoverPickRequest,
    CoverPickResponse,
)
from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickError,
    CoverPickService,
    current_cover_asset,
)
from rag_backend.application.services.carousel.slide_cover_switch import (
    SlideCoverSwitchResult,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_cover_pick import (
    COVER_PICK_STATUS_SWITCHED,
    ERR_COVER_PICK_ASSET_NOT_ALLOWED,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.modules.autopilot import project_cover_offer
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    CarouselProjectWriteOwner,
    cover_pick_service,
)

router = APIRouter(tags=["carousels-cover-pick"])

_CONFLICT_RESPONSES: dict[int | str, dict[str, object]] = {
    status.HTTP_409_CONFLICT: {
        "description": (
            "Typed conflict: the lock version moved, another mutator holds the "
            "project lock, a workflow run or an artifact build is in progress."
        ),
        "model": CarouselConflictResponse,
    },
}


@dataclass(frozen=True)
class CoverPickContext:
    """The request session, the owned project and the picker."""

    db: AsyncSession
    project: CarouselProject
    service: CoverPickService


async def get_cover_pick_context(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> CoverPickContext:
    """404 for an unknown carousel, 403 unless the caller owns it (or is admin)."""
    project = await CarouselAutomationAcl(db).load_project(str(project_id))
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_CAROUSEL_NOT_FOUND
        )
    assert_domain_owner_or_admin(project.owner_id, current_user.to_entity())
    service = cover_pick_service(db, project_cover_offer(db))
    return CoverPickContext(db=db, project=project, service=service)


def _refused(error: CoverPickError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.code
    )


def _raise_unless_switched(result: SlideCoverSwitchResult) -> None:
    """Conflict → 409; a vanished cover → 422; a failed re-render → 422/409."""
    if result.status == AUTOFIX_STATUS_CONFLICT:
        raise CarouselConflictError(
            CarouselConflict.for_code(CONFLICT_CODE_VERSION_CONFLICT)
        )
    if result.status != AUTOFIX_STATUS_FIXED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=ERR_COVER_PICK_ASSET_NOT_ALLOWED,
        )
    if result.render_errors:
        raise_republish_failure(result.render_errors)


@router.get(
    "/{project_id}/cover-options",
    response_model=CoverOptionsResponse,
    summary="The images slide 1 of a POV carousel may show",
)
async def list_cover_options(
    ctx: Annotated[CoverPickContext, Depends(get_cover_pick_context)],
) -> CoverOptionsResponse:
    """Library photos (file present), then the GrokBot offer; current marked."""
    try:
        found = await ctx.service.options(ctx.project)
    except CoverPickError as error:
        raise _refused(error) from error
    return CoverOptionsResponse(
        project_id=str(ctx.project.id),
        current_asset_id=found.current_asset_id,
        options=[
            CoverOptionResponse(
                asset_id=option.asset_id, source=option.source, kind=option.kind
            )
            for option in found.options
        ],
    )


@router.put(
    "/{project_id}/cover",
    response_model=CoverPickResponse,
    summary="Change slide 1's image of a completed POV carousel and re-render",
    responses=_CONFLICT_RESPONSES,
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def pick_cover(
    request: Request,
    body: CoverPickRequest,
    ctx: Annotated[CoverPickContext, Depends(get_cover_pick_context)],
) -> CoverPickResponse:
    """Stage, store under the lock-version CAS, then republish slides + PDFs."""
    command = CoverPickCommand(
        project=ctx.project,
        asset_id=body.asset_id,
        expected_version=body.expected_version,
    )
    try:
        result = await ctx.service.pick(command)
    except CoverPickError as error:
        raise _refused(error) from error
    _raise_unless_switched(result)
    project_id = str(ctx.project.id)
    # The fresh artifacts reflect every pending copy edit too (as republish).
    await CarouselProjectWriteOwner(ctx.db).clear_needs_republish(project_id)
    await ctx.db.commit()
    updated = await CarouselAutomationAcl(ctx.db).load_project(project_id)
    return CoverPickResponse(
        project_id=project_id,
        status=COVER_PICK_STATUS_SWITCHED,
        current_asset_id=current_cover_asset(updated or ctx.project),
        artifact_version=(updated or ctx.project).artifact_version,
    )


__all__ = ["get_cover_pick_context", "router"]
