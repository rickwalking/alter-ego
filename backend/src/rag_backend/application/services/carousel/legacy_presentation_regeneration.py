"""Explicit legacy carousel presentation audit and regeneration."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.artifact_build_service import (
    ArtifactBuildFailure,
    ArtifactBuildRequest,
    ArtifactBuildResult,
    CarouselArtifactBuildService,
    read_project_lock_version,
)
from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthRequest,
    evaluate_carousel_artifacts,
)
from rag_backend.application.services.carousel.presentation_policy import (
    PresentationPolicyError,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review import (
    build_localized_slides,
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.domain.constants.carousel_presentation import (
    LEGACY_PRESENTATION_POLICY_VERSION,
    VALIDATION_STATUS_VALID,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)


class LegacyRegenerationError(RuntimeError):
    """Raised when explicit legacy regeneration cannot complete."""


_ROLLBACK_DIR_NAME = ".rollback"
_ERR_NO_OUTPUT_DIR = "carousel output_dir is missing"
_ERR_NO_SLIDES = "carousel has no persisted slides"
_ERR_PROJECT_NOT_FOUND = "carousel project not found"
_ERR_PROJECT_NOT_FOUND_AFTER_RENDER = "carousel project not found after render"
_ERR_ARTIFACT_BUILD_FAILED = "artifact build failed"
_ERR_UNEXPECTED_BUILD_RESULT = "artifact build returned an unexpected result"
_ERR_VALIDATION_BLOCKED = "presentation validation failed in audit mode"
_ERR_REPAIR_NOT_WIRED = (
    "bounded repair is not available from this CLI; fix violations manually"
)
_MSG_LEGACY_AUDIT_SKIPPED = (
    "legacy_neon_v2 audit skipped presentation union validation; artifact health only"
)


@dataclass(frozen=True)
class RegenerationAuditReport:
    """Audit-only outcome before optional render and artifact promotion."""

    project_id: str
    current_policy_version: str
    target_policy_version: str
    validation_status: str
    blocking: bool
    violation_messages: tuple[str, ...]
    artifact_health_ok: bool
    artifact_health_errors: tuple[str, ...]
    prior_artifact_version: str | None
    backup_path: Path | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class RegenerationResult:
    """Outcome of explicit legacy regeneration."""

    audit: RegenerationAuditReport
    rendered: bool
    artifact_version: str | None
    manifest_path: Path | None


@dataclass(frozen=True)
class RegenerationCommand:
    """Operator command for explicit legacy regeneration."""

    project_id: UUID
    dry_run: bool
    repair: bool
    render: bool
    target_policy_version: str


@dataclass(frozen=True)
class AuditContext:
    """Parameters for auditing a legacy presentation."""

    project: CarouselProject
    slides: Sequence[CarouselSlide]
    target_policy_version: str
    validate_presentation: bool


@dataclass(frozen=True)
class RegeneratePresentationCommand:
    """Parameters for regenerating a legacy presentation."""

    db: AsyncSession
    refinement: CarouselRefinementService
    artifact_build: CarouselArtifactBuildService
    command: RegenerationCommand


def _slides_to_drafts(slides: Sequence[CarouselSlide]) -> list[dict[str, object]]:
    drafts: list[dict[str, object]] = []
    for slide in slides:
        extras = unpack_extras(slide)
        draft: dict[str, object] = {
            "slide_index": slide.slide_number,
            "slide_type": slide.slide_type,
            "heading": slide.heading,
            "body": slide.body,
        }
        draft.update(extras)
        drafts.append(draft)
    return drafts


def _backup_output_root(output_dir: Path) -> Path:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = output_dir / _ROLLBACK_DIR_NAME / stamp
    backup_root.mkdir(parents=True, exist_ok=True)
    for name in ("pt", "en", "images"):
        source = output_dir / name
        if source.is_dir():
            shutil.copytree(source, backup_root / name, dirs_exist_ok=True)
    return backup_root


def _validation_messages(report: dict[str, object]) -> tuple[str, ...]:
    raw = report.get("violations")
    if not isinstance(raw, list):
        return ()
    messages: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        message = item.get("message")
        if isinstance(message, str) and message.strip():
            messages.append(message.strip())
        elif isinstance(code, str) and code.strip():
            messages.append(code.strip())
    return tuple(messages)


def audit_legacy_presentation(
    context: AuditContext,
) -> RegenerationAuditReport:
    """Audit existing PT/EN copy and artifact health without mutating files."""
    current_policy = (
        context.project.presentation_policy_version
        or LEGACY_PRESENTATION_POLICY_VERSION
    )
    notes: list[str] = []
    validation_report: dict[str, object]
    if not context.validate_presentation:
        notes.append(_MSG_LEGACY_AUDIT_SKIPPED)
        validation_report = {
            "validation_status": VALIDATION_STATUS_VALID,
            "blocking": False,
            "violations": [],
        }
    else:
        drafts = _slides_to_drafts(context.slides)
        localized = build_localized_slides(drafts)
        validation_report = validation_report_to_dict(
            validate_localized_slides(
                localized,
                policy_version=context.target_policy_version,
            ),
        )

    health = evaluate_carousel_artifacts(
        CarouselArtifactHealthRequest(project=context.project, slides=context.slides),
    )
    backup_path = None
    if context.project.output_dir:
        backup_path = Path(context.project.output_dir) / _ROLLBACK_DIR_NAME

    return RegenerationAuditReport(
        project_id=str(context.project.id),
        current_policy_version=current_policy,
        target_policy_version=context.target_policy_version,
        validation_status=str(validation_report.get("validation_status", "invalid")),
        blocking=bool(validation_report.get("blocking")),
        violation_messages=_validation_messages(validation_report),
        artifact_health_ok=health.ok,
        artifact_health_errors=health.errors,
        prior_artifact_version=context.project.artifact_version,
        backup_path=backup_path,
        notes=tuple(notes),
    )


async def _load_project_and_slides(
    db: AsyncSession,
    command: RegenerationCommand,
) -> tuple[PostgresCarouselRepository, CarouselProject, list[CarouselSlide]]:
    """Load and validate project existence, slides, and output directory."""
    repo = PostgresCarouselRepository(session=db)
    project = await repo.get_project_by_id(command.project_id)
    if project is None:
        raise ValueError(_ERR_PROJECT_NOT_FOUND)
    slides = await repo.get_slides_by_project(command.project_id)
    if not slides:
        raise ValueError(_ERR_NO_SLIDES)
    if not project.output_dir:
        raise ValueError(_ERR_NO_OUTPUT_DIR)
    return repo, project, list(slides)


def _validate_and_audit(
    project: CarouselProject,
    slides: list[CarouselSlide],
    command: RegenerationCommand,
) -> RegenerationAuditReport:
    """Determine policy version, run audit, and raise on blocking violations."""
    current_policy = (
        project.presentation_policy_version or LEGACY_PRESENTATION_POLICY_VERSION
    )
    validate_presentation = (
        command.render or current_policy != LEGACY_PRESENTATION_POLICY_VERSION
    )
    audit = audit_legacy_presentation(
        AuditContext(
            project=project,
            slides=slides,
            target_policy_version=command.target_policy_version,
            validate_presentation=validate_presentation,
        ),
    )
    if audit.blocking:
        if command.repair:
            raise ValueError(_ERR_REPAIR_NOT_WIRED)
        raise ValueError(_ERR_VALIDATION_BLOCKED)
    return audit


def _backup_and_rebuild_audit(
    project: CarouselProject,
    audit: RegenerationAuditReport,
) -> tuple[Path, RegenerationAuditReport]:
    """Create backup of output dir and rebuild audit report with backup path."""
    output_dir = Path(project.output_dir).resolve()
    backup_path = _backup_output_root(output_dir)
    rebuilt = RegenerationAuditReport(
        project_id=audit.project_id,
        current_policy_version=audit.current_policy_version,
        target_policy_version=audit.target_policy_version,
        validation_status=audit.validation_status,
        blocking=audit.blocking,
        violation_messages=audit.violation_messages,
        artifact_health_ok=audit.artifact_health_ok,
        artifact_health_errors=audit.artifact_health_errors,
        prior_artifact_version=audit.prior_artifact_version,
        backup_path=backup_path,
        notes=audit.notes,
    )
    return backup_path, rebuilt


async def _re_render_and_update_policy(
    repo: PostgresCarouselRepository,
    refinement: CarouselRefinementService,
    command: RegenerationCommand,
) -> CarouselProject:
    """Re-render slides and update the project presentation policy version."""
    await refinement.re_render_slides(command.project_id)
    project = await repo.get_project_by_id(command.project_id)
    if project is None:
        raise ValueError(_ERR_PROJECT_NOT_FOUND_AFTER_RENDER)
    project.presentation_policy_version = command.target_policy_version
    if command.target_policy_version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1:
        try:
            raw_yaml = load_presentation_policy(command.target_policy_version)
            project.presentation_policy_checksum = raw_yaml.checksum
        except PresentationPolicyError:
            project.presentation_policy_checksum = None
    await repo.update_project(project)
    return project


async def regenerate_legacy_presentation(
    params: RegeneratePresentationCommand,
) -> RegenerationResult:
    """Audit, optionally repair, render, and promote a new artifact version."""
    repo, project, slides = await _load_project_and_slides(params.db, params.command)
    audit = _validate_and_audit(project, slides, params.command)

    if params.command.dry_run or not params.command.render:
        return RegenerationResult(
            audit=audit,
            rendered=False,
            artifact_version=project.artifact_version,
            manifest_path=None,
        )

    _backup_path, audit = _backup_and_rebuild_audit(project, audit)
    project = await _re_render_and_update_policy(
        repo, params.refinement, params.command
    )

    lock_version = await read_project_lock_version(params.db, str(project.id))
    build_result = await params.artifact_build.build_and_activate(
        params.db,
        ArtifactBuildRequest(
            project=project,
            slides=await repo.get_slides_by_project(params.command.project_id),
            source_lock_version=lock_version,
            prior_artifact_version=audit.prior_artifact_version,
        ),
    )
    if isinstance(build_result, ArtifactBuildFailure):
        detail = "; ".join(build_result.errors) or _ERR_ARTIFACT_BUILD_FAILED
        raise LegacyRegenerationError(detail)
    if not isinstance(build_result, ArtifactBuildResult):
        raise TypeError(_ERR_UNEXPECTED_BUILD_RESULT)
    await repo.update_project(project)

    return RegenerationResult(
        audit=audit,
        rendered=True,
        artifact_version=build_result.artifact_version,
        manifest_path=build_result.manifest_path,
    )


def default_target_policy_version() -> str:
    """Return the default policy used for explicit legacy regeneration."""
    return DEFAULT_PRESENTATION_POLICY_VERSION


__all__ = [
    "AuditContext",
    "LegacyRegenerationError",
    "RegeneratePresentationCommand",
    "RegenerationAuditReport",
    "RegenerationCommand",
    "RegenerationResult",
    "audit_legacy_presentation",
    "default_target_policy_version",
    "regenerate_legacy_presentation",
]
