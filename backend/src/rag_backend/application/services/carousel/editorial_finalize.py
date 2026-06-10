"""Export rendered slides and mark editorial carousels completed."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.routes.carousels.helpers import merge_design_tokens_with_disk
from rag_backend.application.services.carousel.artifact_build_service import (
    ArtifactBuildFailure,
    ArtifactBuildRequest,
    CarouselArtifactBuildService,
    read_project_lock_version,
    update_project_pdf_paths,
)
from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthReport,
    CarouselArtifactHealthRequest,
    evaluate_carousel_artifacts,
    format_artifact_health_errors,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.models import CarouselStatus
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_ERR_PROJECT_MISSING = "carousel project not found during finalize"
_ERR_OUTPUT_DIR_MISSING = "carousel output_dir missing during finalize"


@dataclass(frozen=True)
class CarouselFinalizeResult:
    completed: bool
    errors: tuple[str, ...]
    artifact_report: CarouselArtifactHealthReport | None = None


async def export_and_complete_carousel(
    db: AsyncSession,
    refinement: CarouselRefinementService,
    project_id: str,
) -> CarouselFinalizeResult:
    """Re-render bilingual slides and set project status to completed."""
    repo = PostgresCarouselRepository(session=db)
    project_uuid = UUID(project_id)
    project = await repo.get_project_by_id(project_uuid)
    if project is None:
        logger.warning(
            "editorial_finalize_skipped",
            project_id=project_id,
            reason="missing_project",
        )
        return CarouselFinalizeResult(completed=False, errors=(_ERR_PROJECT_MISSING,))
    if not project.output_dir:
        logger.warning(
            "editorial_finalize_skipped",
            project_id=project_id,
            reason="missing_output_dir",
        )
        project.mark_failed(_ERR_OUTPUT_DIR_MISSING)
        await repo.update_project(project)
        return CarouselFinalizeResult(
            completed=False,
            errors=(_ERR_OUTPUT_DIR_MISSING,),
        )

    try:
        updated = await refinement.re_render_slides(project_uuid)
    except ValueError as exc:
        logger.warning(
            "editorial_finalize_render_failed",
            project_id=project_id,
            error=str(exc),
        )
        project.mark_failed(str(exc))
        await repo.update_project(project)
        return CarouselFinalizeResult(completed=False, errors=(str(exc),))

    slides = await repo.get_slides_by_project(project_uuid)
    report = evaluate_carousel_artifacts(
        CarouselArtifactHealthRequest(project=updated, slides=slides)
    )
    if not report.ok:
        error_message = format_artifact_health_errors(report.errors)
        logger.warning(
            "editorial_finalize_artifacts_failed",
            project_id=project_id,
            errors=list(report.errors),
        )
        updated.mark_failed(error_message)
        await repo.update_project(updated)
        return CarouselFinalizeResult(
            completed=False,
            errors=report.errors,
            artifact_report=report,
        )

    source_lock_version = await read_project_lock_version(db, project_id)
    build_result = await CarouselArtifactBuildService().build_and_activate(
        db,
        ArtifactBuildRequest(
            project=updated,
            slides=slides,
            source_lock_version=source_lock_version,
            prior_artifact_version=updated.artifact_version,
        ),
    )
    if isinstance(build_result, ArtifactBuildFailure):
        if ERR_ARTIFACT_BUILD_CONFLICT in build_result.errors:
            logger.warning(
                "editorial_finalize_artifact_conflict",
                project_id=project_id,
                artifact_version=build_result.artifact_version,
            )
            return CarouselFinalizeResult(
                completed=False,
                errors=build_result.errors,
                artifact_report=report,
            )
        error_message = format_artifact_health_errors(build_result.errors)
        updated.mark_failed(error_message)
        await repo.update_project(updated)
        return CarouselFinalizeResult(
            completed=False,
            errors=build_result.errors,
            artifact_report=report,
        )

    updated.artifact_version = build_result.artifact_version
    update_project_pdf_paths(updated)
    updated.update_status(CarouselStatus.COMPLETED)
    if updated.output_dir:
        updated.design_tokens = merge_design_tokens_with_disk(updated)
    await repo.update_project(updated)
    return CarouselFinalizeResult(
        completed=True,
        errors=(),
        artifact_report=report,
    )


async def finalize_carousel_after_images_approval(
    db: AsyncSession,
    project_id: str,
) -> CarouselFinalizeResult:
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
    return await export_and_complete_carousel(db, refinement, project_id)


__all__ = [
    "CarouselFinalizeResult",
    "export_and_complete_carousel",
    "finalize_carousel_after_images_approval",
]
