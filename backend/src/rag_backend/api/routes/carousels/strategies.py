"""Carousel slide-layout strategy routes.

Thin HTTP adapters (AE-0120). The list + apply endpoints delegate their data
operations to the presentation :class:`PresentationHandlers` (via the
presentation facade): listing reads the strategy registry behind the handler, and
applying validates the strategy + project status at the edge then runs the
refinement re-render through the handler. The route no longer constructs the
refinement service / repository / registry directly.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.application.services.carousel.strategy_handlers import (
    ApplyStrategyResponse,
    StrategyListResponse,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.presentation import PresentationHandlers

logger = get_logger()

_ERR_STRATEGY_NOT_FOUND = "Unknown strategy: {}"
_ERR_PROJECT_NOT_FOUND = "Project not found"
_ERR_PROJECT_NOT_COMPLETED = "Carousel not completed"
_MSG_STRATEGY_APPLIED = "Slides re-rendered with new strategy"
_STRATEGY_NAME_MIN_LENGTH = 1
_STRATEGY_NAME_MAX_LENGTH = 50

router = APIRouter(
    tags=["carousels-strategies"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/strategies")
async def list_strategies(
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> StrategyListResponse:
    return handlers.list_strategies()


@router.put("/{project_id}/strategy")
async def apply_strategy(
    project_id: UUID,
    name: Annotated[
        str,
        Query(
            min_length=_STRATEGY_NAME_MIN_LENGTH,
            max_length=_STRATEGY_NAME_MAX_LENGTH,
            description="Strategy name to apply",
        ),
    ],
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> ApplyStrategyResponse:
    if not handlers.strategy_exists(name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_ERR_STRATEGY_NOT_FOUND.format(name),
        )

    project = await handlers.get_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_ERR_PROJECT_NOT_FOUND,
        )
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_ERR_PROJECT_NOT_COMPLETED,
        )

    await handlers.apply_strategy(project_id, name)

    logger.info(
        "strategy_applied",
        project_id=str(project_id),
        strategy=name,
    )

    return ApplyStrategyResponse(
        project_id=project_id,
        strategy=name,
        message=_MSG_STRATEGY_APPLIED,
    )
