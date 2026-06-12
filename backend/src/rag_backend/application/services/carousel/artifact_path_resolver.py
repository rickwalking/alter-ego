"""Resolve carousel artifact serving paths with legacy fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag_backend.application.services.carousel.artifact_index_reconciler import (
    reconcile_current_index,
)
from rag_backend.application.services.carousel.artifact_path_safety import (
    resolve_confined_slide_image,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_CURRENT_INDEX_FILENAME,
    ARTIFACT_MANIFEST_FILENAME,
    ARTIFACT_VERSIONS_DIR,
)
from rag_backend.domain.models import CarouselProject


@dataclass(frozen=True)
class ArtifactServingPaths:
    """Resolved filesystem paths for serving carousel artifacts."""

    project_root: Path
    serving_root: Path
    legacy_mode: bool
    artifact_version: str | None


@dataclass(frozen=True)
class _ArtifactPaths:
    """Resolved base artifact paths shared by individual resolvers."""

    project_root: Path
    version_root: Path | None
    images_dir: Path
    manifest_path: Path
    current_index_path: Path


def _resolve_base(project: CarouselProject) -> _ArtifactPaths | None:
    """Resolve base artifact paths. Returns None if output_dir is missing."""
    if not project.output_dir:
        return None
    project_root = Path(project.output_dir).resolve()
    version_root: Path | None = None
    if project.artifact_version:
        vr = project_root / ARTIFACT_VERSIONS_DIR / project.artifact_version
        version_root = vr if vr.is_dir() else None
    images_dir = version_root / "images" if version_root else project_root / "images"
    manifest_path = (
        version_root / ARTIFACT_MANIFEST_FILENAME
        if version_root
        else project_root / ARTIFACT_MANIFEST_FILENAME
    )
    current_index_path = project_root / ARTIFACT_CURRENT_INDEX_FILENAME
    return _ArtifactPaths(
        project_root=project_root,
        version_root=version_root,
        images_dir=images_dir,
        manifest_path=manifest_path,
        current_index_path=current_index_path,
    )


def resolve_and_reconcile_serving_paths(
    project: CarouselProject,
) -> ArtifactServingPaths | None:
    """Resolve serving root from database artifact version with legacy fallback.

    This is the only resolver that reconciles the current index; individual
    path resolvers call the lighter _resolve_base() instead.
    """
    if not project.output_dir:
        return None
    reconcile_current_index(project)
    project_root = Path(project.output_dir).resolve()
    version_root: Path | None = None
    if project.artifact_version:
        vr = project_root / ARTIFACT_VERSIONS_DIR / project.artifact_version
        version_root = vr if vr.is_dir() else None
    return ArtifactServingPaths(
        project_root=project_root,
        serving_root=version_root or project_root,
        legacy_mode=version_root is None,
        artifact_version=project.artifact_version,
    )


def resolve_language_dir(project: CarouselProject, language: str) -> Path | None:
    """Return the directory containing rendered slides for a locale."""
    paths = _resolve_base(project)
    if paths is None:
        return None
    serving_root = paths.version_root if paths.version_root else paths.project_root
    return serving_root / language


def resolve_hd_dir(project: CarouselProject, language: str) -> Path | None:
    """Return the HD slide directory for a locale."""
    language_dir = resolve_language_dir(project, language)
    if language_dir is None:
        return None
    return language_dir / HD_SUBDIR_NAME


def resolve_shared_images_dir(project: CarouselProject) -> Path | None:
    """Return the directory containing raw generated slide images."""
    paths = _resolve_base(project)
    if paths is None:
        return None
    return paths.project_root / SHARED_IMAGES_DIR_NAME


def resolve_manifest_path(project: CarouselProject) -> Path | None:
    """Return artifact-manifest.json for the active version when versioned."""
    paths = _resolve_base(project)
    if paths is None or paths.version_root is None:
        return None
    return paths.manifest_path


def resolve_current_index_path(project: CarouselProject) -> Path | None:
    """Return current.json index path under the project root."""
    paths = _resolve_base(project)
    if paths is None:
        return None
    return paths.current_index_path


def resolve_pdf_path(project: CarouselProject, language: str) -> Path | None:
    """Resolve carousel.pdf for a locale within the active serving root."""
    language_dir = resolve_language_dir(project, language)
    if language_dir is None:
        return None
    candidate = language_dir / "carousel.pdf"
    if candidate.is_file():
        return candidate
    return None


def resolve_slide_image_path(
    project: CarouselProject,
    language: str,
    filename: str,
) -> Path | None:
    """Resolve a rendered slide image from standard then HD directories."""
    language_dir = resolve_language_dir(project, language)
    if language_dir is None:
        return None
    standard = resolve_confined_slide_image(language_dir, filename)
    if standard is not None:
        return standard
    hd_dir = language_dir / HD_SUBDIR_NAME
    return resolve_confined_slide_image(hd_dir, filename)


def supported_languages(project: CarouselProject) -> tuple[str, ...]:
    """Return locales that have rendered slide directories."""
    languages: list[str] = []
    for language in (LANGUAGE_PT, LANGUAGE_EN):
        language_dir = resolve_language_dir(project, language)
        if language_dir is not None and language_dir.is_dir():
            languages.append(language)
    return tuple(languages)


__all__ = [
    "ArtifactServingPaths",
    "resolve_and_reconcile_serving_paths",
    "resolve_current_index_path",
    "resolve_hd_dir",
    "resolve_language_dir",
    "resolve_manifest_path",
    "resolve_pdf_path",
    "resolve_shared_images_dir",
    "resolve_slide_image_path",
    "supported_languages",
]
