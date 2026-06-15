"""Admin carousel maintenance routes.

Thin HTTP adapters (AE-0120). The bulk design-token refresh and slide-render
endpoints delegate their data operations to the presentation
:class:`PresentationHandlers` (via the presentation facade): the design-token
refresh persists through the AE-0118 single write owner + the platform UoW (the
route never calls ``session.commit()`` directly), and the render-slides loop runs
through the refinement service behind the handler. The route supplies the on-disk
``_slide_missing`` skip probe (it owns the rendering/disk details) and maps the
handler's counters to the response model.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from rag_backend.api.dependencies import require_admin
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.application.services.carousel.design_token_utils import (
    _has_rendered_slides,
)
from rag_backend.domain.models import CarouselProject, User
from rag_backend.modules.presentation import PresentationHandlers

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
    """On-disk ``_slide_missing`` skip probe (a ``SlideMissingPredicate`` callable).

    Keeps the rendering/disk details at the route edge while the handler's bulk
    loop invokes it per project. Byte-identical to the legacy admin
    ``_slide_missing`` helper.
    """
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
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> RefreshDesignTokensResponse:
    projects = await handlers.list_completed_projects()
    result = await handlers.refresh_design_tokens(projects)
    return RefreshDesignTokensResponse(
        total=len(projects),
        updated=result.updated,
        failed=result.failed,
        errors=result.errors,
    )


@router.post(
    "/admin/carousels/render-slides",
    responses={
        403: {"description": "Admin access required"},
    },
)
async def render_missing_slides(
    _admin: Annotated[User, Depends(require_admin)],
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> RenderSlidesResponse:
    projects = await handlers.list_completed_projects()
    result = await handlers.render_slides(projects, _slide_missing)
    return RenderSlidesResponse(
        total=len(projects),
        updated=result.updated,
        skipped=result.skipped,
        failed=result.failed,
        errors=result.errors,
    )
