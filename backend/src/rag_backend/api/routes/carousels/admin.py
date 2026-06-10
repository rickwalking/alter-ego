from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies import require_admin
from rag_backend.application.services.carousel_template.design import (
    generate_design_tokens,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus, User
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository
from rag_backend.infrastructure.database.config import get_session

from .deps import get_carousel_refinement, get_carousel_repo
from .helpers import _has_rendered_slides

router = APIRouter(tags=["carousels-admin"])


class RefreshDesignTokensResponse(BaseModel):
    total: int
    updated: int
    failed: int
    errors: list[str]


class RenderSlidesResponse(BaseModel):
    total: int
    updated: int
    skipped: int
    failed: int
    errors: list[str]


def _slide_missing(project: CarouselProject) -> bool:
    output_dir = project.output_dir
    if not output_dir:
        return True
    pt_ok = _has_rendered_slides(project, "pt")
    if not pt_ok:
        return True
    en_ok = _has_rendered_slides(project, "en")
    return not en_ok


@router.post(
    "/admin/carousels/refresh-design-tokens",
    responses={
        403: {"description": "Admin access required"},
    },
)
async def refresh_design_tokens(
    _admin: Annotated[User, Depends(require_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshDesignTokensResponse:
    projects = await repo.get_all_projects(
        status=CarouselStatus.COMPLETED, limit=1000, offset=0
    )

    updated = 0
    failed = 0
    errors: list[str] = []

    for project in projects:
        try:
            project.design_tokens = generate_design_tokens(project)
            await repo.update_project(project)
            updated += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{project.id}: {exc}")

    await session.commit()

    return RefreshDesignTokensResponse(
        total=len(projects),
        updated=updated,
        failed=failed,
        errors=errors,
    )


@router.post(
    "/admin/carousels/render-slides",
    responses={
        403: {"description": "Admin access required"},
    },
)
async def render_missing_slides(
    _admin: Annotated[User, Depends(require_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    refinement: Annotated[CarouselRefinementService, Depends(get_carousel_refinement)],
) -> RenderSlidesResponse:
    projects = await repo.get_all_projects(
        status=CarouselStatus.COMPLETED, limit=1000, offset=0
    )

    updated = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    for project in projects:
        if not _slide_missing(project):
            skipped += 1
            continue
        try:
            await refinement.re_render_slides(project.id)
            updated += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{project.id}: {exc}")

    return RenderSlidesResponse(
        total=len(projects),
        updated=updated,
        skipped=skipped,
        failed=failed,
        errors=errors,
    )
