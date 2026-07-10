"""Staging, manifest writing, and compare-and-swap artifact activation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.artifact_build_support import (
    build_manifest,
    ensure_promoted,
    populate_staging,
    version_input_from_request,
    write_current_index,
    write_manifest,
)
from rag_backend.application.services.carousel.artifact_build_types import (
    ArtifactBuildFailure,
    ArtifactBuildRequest,
    ArtifactBuildResult,
    ArtifactVersionInput,
    compute_artifact_version,
    compute_design_fingerprint,
    compute_operation_id,
    compute_slides_fingerprint,
)
from rag_backend.application.services.carousel.artifact_path_resolver import (
    resolve_language_dir,
)
from rag_backend.domain.constants import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_MANIFEST_FILENAME,
    ARTIFACT_STAGING_DIR,
    ARTIFACT_VERSIONS_DIR,
    ERR_ARTIFACT_BUILD_CONFLICT,
)
from rag_backend.domain.constants.carousel_presentation import (
    ARTIFACT_BUILD_STATUS_FAILED,
    ARTIFACT_BUILD_STATUS_READY,
    ARTIFACT_BUILD_STATUS_STAGING,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_artifact_build import CarouselArtifactBuild
from rag_backend.infrastructure.database.carousel_artifact_build_repository import (
    PostgresCarouselArtifactBuildRepository,
    _ActivateBuildParams,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_PDF_FILENAME = "carousel.pdf"


class ActivateExistingCommand(TypedDict):
    db: AsyncSession
    build_repo: PostgresCarouselArtifactBuildRepository
    request: ArtifactBuildRequest
    artifact_version: str
    version_dir: Path
    manifest_path: Path
    project_root: Path


class CarouselArtifactBuildService:
    """Build immutable artifact versions under project output_dir."""

    async def build_and_activate(
        self,
        db: AsyncSession,
        request: ArtifactBuildRequest,
    ) -> ArtifactBuildResult | ArtifactBuildFailure:
        """Stage legacy outputs, write manifest, promote, and activate."""
        if not request.project.output_dir:
            return ArtifactBuildFailure(
                artifact_version="",
                errors=("carousel output_dir is missing",),
            )
        project_root = Path(request.project.output_dir).resolve()
        version_input = version_input_from_request(request)
        artifact_version = compute_artifact_version(version_input)
        operation_id = compute_operation_id(
            str(request.project.id),
            request.source_lock_version,
            artifact_version,
        )
        build_repo = PostgresCarouselArtifactBuildRepository(db)
        existing = await build_repo.get_by_project_and_version(
            request.project.id,
            artifact_version,
        )
        version_dir = project_root / ARTIFACT_VERSIONS_DIR / artifact_version
        if existing is not None and version_dir.is_dir():
            manifest_path = version_dir / ARTIFACT_MANIFEST_FILENAME
            if manifest_path.is_file():
                return await self._activate_existing(
                    ActivateExistingCommand(
                        db=db,
                        build_repo=build_repo,
                        request=request,
                        artifact_version=artifact_version,
                        version_dir=version_dir,
                        manifest_path=manifest_path,
                        project_root=project_root,
                    ),
                )

        staging_dir = project_root / ARTIFACT_STAGING_DIR / operation_id
        build_record = CarouselArtifactBuild(
            project_id=request.project.id,
            artifact_version=artifact_version,
            operation_id=operation_id,
            source_lock_version=request.source_lock_version,
            status=ARTIFACT_BUILD_STATUS_STAGING,
            staging_path=str(staging_dir),
        )
        await build_repo.upsert_build(build_record)
        try:
            populate_staging(project_root, staging_dir)
            manifest = build_manifest(request, artifact_version, staging_dir)
            manifest_path = staging_dir / ARTIFACT_MANIFEST_FILENAME
            write_manifest(manifest_path, manifest)
            ensure_promoted(staging_dir, version_dir)
            build_record.status = ARTIFACT_BUILD_STATUS_READY
            build_record.staging_path = None
            await build_repo.upsert_build(build_record)
            lock_version = await build_repo.activate_build(
                params=_ActivateBuildParams(
                    project_id=request.project.id,
                    artifact_version=artifact_version,
                    source_lock_version=request.source_lock_version,
                    prior_artifact_version=request.prior_artifact_version,
                ),
            )
            await db.commit()
            # AE-0313 r4: write the on-disk index ONLY after the activation CAS
            # commit succeeds — a CAS-losing concurrent build raises above and
            # never reaches here, so current.json can never name a version that
            # failed to activate in the DB.
            write_current_index(project_root, artifact_version)
            request.project.artifact_version = artifact_version
            logger.info(
                "carousel_artifact_promoted",
                project_id=str(request.project.id),
                artifact_version=artifact_version,
                operation_id=operation_id,
            )
            return ArtifactBuildResult(
                artifact_version=artifact_version,
                operation_id=operation_id,
                lock_version=lock_version,
                manifest_path=version_dir / ARTIFACT_MANIFEST_FILENAME,
                version_dir=version_dir,
            )
        except ValueError as exc:
            await build_repo.mark_build_status(
                request.project.id,
                artifact_version,
                ARTIFACT_BUILD_STATUS_FAILED,
            )
            await db.commit()
            if str(exc) == ERR_ARTIFACT_BUILD_CONFLICT:
                return ArtifactBuildFailure(
                    artifact_version=artifact_version,
                    errors=(ERR_ARTIFACT_BUILD_CONFLICT,),
                )
            return ArtifactBuildFailure(
                artifact_version=artifact_version,
                errors=(str(exc),),
            )
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

    @staticmethod
    async def _activate_existing(
        command: ActivateExistingCommand,
    ) -> ArtifactBuildResult | ArtifactBuildFailure:
        operation_id = compute_operation_id(
            str(command["request"].project.id),
            command["request"].source_lock_version,
            command["artifact_version"],
        )
        try:
            lock_version = await command["build_repo"].activate_build(
                params=_ActivateBuildParams(
                    project_id=command["request"].project.id,
                    artifact_version=command["artifact_version"],
                    source_lock_version=command["request"].source_lock_version,
                    prior_artifact_version=command["request"].prior_artifact_version,
                ),
            )
            await command["db"].commit()
            # AE-0313 r3: the idempotent re-activation path must refresh the
            # on-disk index too — without this, current.json lagged the DB until
            # a lazy read-path reconciler ran, so a republish→download with no
            # intervening state read served the prior version's PDF.
            write_current_index(command["project_root"], command["artifact_version"])
            command["request"].project.artifact_version = command["artifact_version"]
            return ArtifactBuildResult(
                artifact_version=command["artifact_version"],
                operation_id=operation_id,
                lock_version=lock_version,
                manifest_path=command["manifest_path"],
                version_dir=command["version_dir"],
            )
        except ValueError as exc:
            await command["db"].commit()
            if str(exc) == ERR_ARTIFACT_BUILD_CONFLICT:
                return ArtifactBuildFailure(
                    artifact_version=command["artifact_version"],
                    errors=(ERR_ARTIFACT_BUILD_CONFLICT,),
                )
            return ArtifactBuildFailure(
                artifact_version=command["artifact_version"],
                errors=(str(exc),),
            )


async def read_project_lock_version(
    db: AsyncSession,
    project_id: str,
) -> int:
    """Return current carousel project lock_version."""
    model = await db.get(CarouselProjectModel, project_id)
    if model is None:
        return 1
    return int(model.lock_version or 1)


def update_project_pdf_paths(project: CarouselProject) -> None:
    """Point project PDF paths at the active version directory."""
    if not project.output_dir or not project.artifact_version:
        return
    pt_pdf = resolve_language_dir(project, LANGUAGE_PT)
    en_pdf = resolve_language_dir(project, LANGUAGE_EN)
    if pt_pdf is not None:
        candidate = pt_pdf / _PDF_FILENAME
        if candidate.is_file():
            project.pdf_path = str(candidate)
    if en_pdf is not None:
        candidate = en_pdf / _PDF_FILENAME
        if candidate.is_file():
            project.pdf_path_en = str(candidate)


__all__ = [
    "ArtifactBuildFailure",
    "ArtifactBuildRequest",
    "ArtifactBuildResult",
    "ArtifactVersionInput",
    "CarouselArtifactBuildService",
    "compute_artifact_version",
    "compute_design_fingerprint",
    "compute_operation_id",
    "compute_slides_fingerprint",
    "read_project_lock_version",
    "update_project_pdf_paths",
]
