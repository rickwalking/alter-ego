from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.application.services.carousel.strategy_handlers import (
    ApplyStrategyResponse,
    StrategyInfo,
    StrategyListResponse,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.protocols import CarouselRefinementService, CarouselRepository
from rag_backend.infrastructure.logging import get_logger

from .deps import get_carousel_refinement, get_carousel_repo, get_strategy_registry

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


@dataclass
class _ApplyStrategyContext:
    """Bundle apply_strategy dependencies (max 3 route args)."""

    refinement: CarouselRefinementService
    repo: CarouselRepository
    registry: SlideLayoutRegistry


def _resolve_strategy_context(
    refinement: Annotated[CarouselRefinementService, Depends(get_carousel_refinement)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    registry: Annotated[SlideLayoutRegistry, Depends(get_strategy_registry)],
) -> _ApplyStrategyContext:
    """Resolve strategy dependencies into a single context object."""
    return _ApplyStrategyContext(refinement=refinement, repo=repo, registry=registry)


@router.get("/strategies")
async def list_strategies(
    registry: Annotated[SlideLayoutRegistry, Depends(get_strategy_registry)],
) -> StrategyListResponse:
    raw = registry.list()
    return StrategyListResponse(
        strategies=[
            StrategyInfo(name=r["name"], display_name=r["display_name"]) for r in raw
        ]
    )


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
    ctx: Annotated[_ApplyStrategyContext, Depends(_resolve_strategy_context)],
) -> ApplyStrategyResponse:
    try:
        ctx.registry.get(name)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_ERR_STRATEGY_NOT_FOUND.format(name),
        ) from None

    project = await ctx.repo.get_project_by_id(project_id)
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

    await ctx.refinement.re_render_slides(project_id, strategy=name)

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
