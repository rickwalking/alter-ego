"""Export rendered slides and mark editorial carousels completed."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.artifact_build_service import (
    update_project_pdf_paths,
)
from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthReport,
    CarouselArtifactHealthRequest,
    evaluate_carousel_artifacts,
    format_artifact_health_errors,
)
from rag_backend.application.services.carousel.design_token_utils import (
    merge_design_tokens_with_disk,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.presentation import (
    ArtifactActivation,
    CarouselArtifactBuildAdapter,
)

logger = get_logger()

_ERR_PROJECT_MISSING = "carousel project not found during finalize"
_ERR_OUTPUT_DIR_MISSING = "carousel output_dir missing during finalize"
# Defensive: a successful (no-errors) build path must yield an activation result.
_ERR_BUILD_RESULT_MISSING = "artifact build returned no activation despite no errors"


@dataclass(frozen=True)
class _RerenderTarget:
    project: CarouselProject
    project_id: str


@dataclass(frozen=True)
class _BuildTarget:
    project_id: str
    updated: CarouselProject


@dataclass(frozen=True)
class CarouselFinalizeResult:
    completed: bool
    errors: tuple[str, ...]
    artifact_report: CarouselArtifactHealthReport | None = None


async def _fail_finalize(
    repo: PostgresCarouselRepository,
    project: CarouselProject,
    error_message: str,
) -> None:
    """Persist a finalize failure UNLESS the project is already completed.

    AE-0313: a re-finalize/republish on a ``completed`` project must never
    ``mark_failed`` it — a false-negative health check or a transient build
    error would otherwise corrupt a healthy, already-served carousel. The
    project stays ``completed`` on its current artifact version and the error
    is returned to the caller instead. First-time finalize (project not yet
    completed) keeps its existing mark_failed behavior.
    """
    if project.status == CarouselStatus.COMPLETED:
        logger.warning(
            "editorial_finalize_failed_preserved_completed",
            project_id=str(project.id),
            error=error_message,
        )
        return
    project.mark_failed(error_message)
    await repo.update_project(project)


async def _guard_project_exists(
    repo: PostgresCarouselRepository,
    project_id: str,
) -> tuple[CarouselProject | None, CarouselFinalizeResult | None]:
    project = await repo.get_project_by_id(UUID(project_id))
    if project is None:
        logger.warning(
            "editorial_finalize_skipped",
            project_id=project_id,
            reason="missing_project",
        )
        return None, CarouselFinalizeResult(
            completed=False, errors=(_ERR_PROJECT_MISSING,)
        )
    if not project.output_dir:
        logger.warning(
            "editorial_finalize_skipped",
            project_id=project_id,
            reason="missing_output_dir",
        )
        await _fail_finalize(repo, project, _ERR_OUTPUT_DIR_MISSING)
        return None, CarouselFinalizeResult(
            completed=False,
            errors=(_ERR_OUTPUT_DIR_MISSING,),
        )
    return project, None


async def _try_rerender_slides(
    repo: PostgresCarouselRepository,
    refinement: CarouselRefinementService,
    target: _RerenderTarget,
) -> tuple[CarouselProject, tuple[str, ...]]:
    try:
        updated = await refinement.re_render_slides(UUID(target.project_id))
    except ValueError as exc:
        logger.warning(
            "editorial_finalize_render_failed",
            project_id=target.project_id,
            error=str(exc),
        )
        await _fail_finalize(repo, target.project, str(exc))
        return target.project, (str(exc),)
    else:
        return updated, ()


async def _verify_artifacts(
    repo: PostgresCarouselRepository,
    project_id: str,
    updated: CarouselProject,
) -> tuple[tuple[str, ...], CarouselArtifactHealthReport | None]:
    slides = await repo.get_slides_by_project(UUID(project_id))
    report = evaluate_carousel_artifacts(
        CarouselArtifactHealthRequest(
            project=updated,
            slides=slides,
            validate_pre_promotion=True,
        )
    )
    if report.ok:
        return (), None
    error_message = format_artifact_health_errors(report.errors)
    logger.warning(
        "editorial_finalize_artifacts_failed",
        project_id=project_id,
        errors=list(report.errors),
    )
    await _fail_finalize(repo, updated, error_message)
    return report.errors, report


async def _try_build_artifacts(
    db: AsyncSession,
    repo: PostgresCarouselRepository,
    target: _BuildTarget,
) -> tuple[
    tuple[str, ...], CarouselArtifactHealthReport | None, ArtifactActivation | None
]:
    # AE-0121: the artifact build/activation is a PRESENTATION operation invoked
    # through the presentation public facade (editorial → presentation). The
    # adapter delegates UNCHANGED to CarouselArtifactBuildService.build_and_activate,
    # so the compound artifact_version ↔ lock_version CAS, the source-lock-version
    # read, and the slide load are byte-identical to the legacy direct call.
    adapter = CarouselArtifactBuildAdapter(db, repo)
    activation = await adapter.build_and_activate(target.project_id)
    if activation.ok:
        return (), None, activation
    if ERR_ARTIFACT_BUILD_CONFLICT not in activation.errors:
        error_message = format_artifact_health_errors(activation.errors)
        await _fail_finalize(repo, target.updated, error_message)
    else:
        logger.warning(
            "editorial_finalize_artifact_conflict",
            project_id=target.project_id,
            artifact_version=activation.artifact_version,
        )
    return activation.errors, None, None


async def export_and_complete_carousel(
    db: AsyncSession,
    refinement: CarouselRefinementService,
    project_id: str,
) -> CarouselFinalizeResult:
    """Re-render bilingual slides and set project status to completed."""
    repo = PostgresCarouselRepository(session=db)
    project, result = await _guard_project_exists(repo, project_id)
    if result is not None:
        return result

    updated, errors = await _try_rerender_slides(
        repo, refinement, _RerenderTarget(project=project, project_id=project_id)
    )
    artifact_report: CarouselArtifactHealthReport | None = None

    if not errors:
        errors, artifact_report = await _verify_artifacts(repo, project_id, updated)

    build_result: ArtifactActivation | None = None
    if not errors:
        errors, artifact_report, build_result = await _try_build_artifacts(
            db,
            repo,
            _BuildTarget(project_id=project_id, updated=updated),
        )

    if errors:
        return CarouselFinalizeResult(
            completed=False,
            errors=errors,
            artifact_report=artifact_report,
        )

    if build_result is None:
        raise RuntimeError(_ERR_BUILD_RESULT_MISSING)
    updated.artifact_version = build_result.artifact_version
    update_project_pdf_paths(updated)
    # AE-0107 boundary: the terminal-finalization write persists the WO fields
    # (status/error_message) ATOMICALLY with the deferred Phase-5 presentation
    # columns (design_tokens/pdf_path/artifact_version) in this single
    # repo.update_project commit. Splitting status out to CarouselProjectWriteOwner
    # would break that atomicity (two commits) — so this terminal write stays on the
    # legacy W1 persistence path per the AE-0105 field map until Phase 5 extracts
    # presentation. AE-0107 owns the workflow-PHASE writes (sync_phase/assign_reviewer/
    # set_phase_status/resume-lock), not this atomic terminal artifact write.
    updated.update_status(CarouselStatus.COMPLETED)
    if updated.output_dir:
        updated.design_tokens = merge_design_tokens_with_disk(updated)
    await repo.update_project(updated)
    return CarouselFinalizeResult(
        completed=True,
        errors=(),
        artifact_report=artifact_report,
    )


async def finalize_carousel_after_images_approval(
    db: AsyncSession,
    project_id: str,
) -> CarouselFinalizeResult:
    """Build refinement service from DI container and export slides after image gate."""
    from rag_backend.application.services.carousel.refinement_service import (
        CarouselRefinementConfig,
    )
    from rag_backend.application.services.carousel.refinement_service import (
        CarouselRefinementService as CarouselRefinementServiceImpl,
    )
    from rag_backend.infrastructure.container import get_container
    from rag_backend.infrastructure.database.carousel_repository import (
        PostgresCarouselRepository,
    )

    container = get_container()
    refinement = CarouselRefinementServiceImpl(
        CarouselRefinementConfig(
            repository=PostgresCarouselRepository(db),
            llm_service=container.llm_service(),
            image_registry=container.image_provider_registry(),
            export_service=container.export_service(),
            pdf_slide_builder=container.pdf_slide_builder(),
            strategy_registry=container.strategy_registry(),
        )
    )
    return await export_and_complete_carousel(db, refinement, project_id)


__all__ = [
    "CarouselFinalizeResult",
    "export_and_complete_carousel",
    "finalize_carousel_after_images_approval",
]
