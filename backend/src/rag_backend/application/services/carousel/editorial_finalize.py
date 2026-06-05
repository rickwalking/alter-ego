"""Export rendered slides and mark editorial carousels completed."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels.helpers import _merge_design_tokens_with_disk
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


async def export_and_complete_carousel(
    db: AsyncSession,
    refinement: CarouselRefinementService,
    project_id: str,
) -> None:
    """Re-render bilingual slides and set project status to completed."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None or not project.output_dir:
        logger.warning(
            "editorial_finalize_skipped",
            project_id=project_id,
            reason="missing_output_dir",
        )
        return

    try:
        updated = await refinement.re_render_slides(UUID(project_id))
    except ValueError as exc:
        logger.warning(
            "editorial_finalize_render_failed",
            project_id=project_id,
            error=str(exc),
        )
        return

    updated.update_status(CarouselStatus.COMPLETED)
    if updated.output_dir:
        updated.design_tokens = _merge_design_tokens_with_disk(updated)
    await repo.update_project(updated)


async def finalize_carousel_after_images_approval(
    db: AsyncSession,
    project_id: str,
) -> None:
    """Build refinement service from DI container and export slides after image gate."""
    from rag_backend.application.services.carousel.refinement_service import (
        CarouselRefinementService as CarouselRefinementServiceImpl,
    )
    from rag_backend.infrastructure.container import get_container
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    container = get_container()
    refinement = CarouselRefinementServiceImpl(
        repository=PostgresCarouselRepository(db),
        llm_service=container.llm_service(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        pdf_slide_builder=container.pdf_slide_builder(),
        strategy_registry=container.strategy_registry(),
    )
    await export_and_complete_carousel(db, refinement, project_id)


__all__ = ["export_and_complete_carousel", "finalize_carousel_after_images_approval"]
