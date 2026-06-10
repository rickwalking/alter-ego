"""Filesystem helpers for carousel artifact build staging and manifests."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from rag_backend.application.services.carousel.artifact_build_types import (
    ArtifactBuildRequest,
    ArtifactVersionInput,
    compute_design_fingerprint,
    compute_slides_fingerprint,
)
from rag_backend.application.services.carousel.artifact_manifest import (
    ArtifactPdfEntry,
    ArtifactRawImageEntry,
    ArtifactSlideFileEntry,
    CarouselArtifactManifest,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
)
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_CURRENT_INDEX_FILENAME,
    ERR_ARTIFACT_STAGING_INCOMPLETE,
    EXPORTER_CONTRACT_VERSION,
    RENDERER_CONTRACT_VERSION,
)
from rag_backend.domain.constants.carousel_presentation import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models import CarouselProject

_PDF_FILENAME = "carousel.pdf"
_SLIDE_FILENAME_TEMPLATE = "slide_{}.jpg"


def version_input_from_request(request: ArtifactBuildRequest) -> ArtifactVersionInput:
    from rag_backend.domain.constants import CAROUSEL_HEIGHT, CAROUSEL_WIDTH

    return ArtifactVersionInput(
        project_id=str(request.project.id),
        source_lock_version=request.source_lock_version,
        presentation_policy_version=(
            request.project.presentation_policy_version
            or DEFAULT_PRESENTATION_POLICY_VERSION
        ),
        presentation_policy_checksum=request.project.presentation_policy_checksum,
        template_version=request.project.template_version,
        slides_fingerprint=compute_slides_fingerprint(request.slides),
        design_fingerprint=compute_design_fingerprint(request.project),
        creator_asset_hash=creator_asset_hash(request.project),
        export_width=CAROUSEL_WIDTH,
        export_height=CAROUSEL_HEIGHT,
    )


def creator_asset_hash(project: CarouselProject) -> str | None:
    staged_path = project.creator_asset_staged_path
    if not staged_path or not project.output_dir:
        return None
    asset_path = Path(project.output_dir).resolve() / staged_path
    if not asset_path.is_file():
        return None
    return sha256_file(asset_path)


def populate_staging(project_root: Path, staging_dir: Path) -> None:
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    for language in (LANGUAGE_PT, LANGUAGE_EN):
        source = project_root / language
        if source.is_dir():
            shutil.copytree(source, staging_dir / language)
    images_source = project_root / SHARED_IMAGES_DIR_NAME
    if images_source.is_dir():
        shutil.copytree(images_source, staging_dir / SHARED_IMAGES_DIR_NAME)


def build_manifest(
    request: ArtifactBuildRequest,
    artifact_version: str,
    staging_dir: Path,
) -> CarouselArtifactManifest:
    expected = tuple(sorted({slide.slide_number for slide in request.slides}))
    return CarouselArtifactManifest(
        project_id=str(request.project.id),
        artifact_version=artifact_version,
        presentation_policy_version=(
            request.project.presentation_policy_version
            or DEFAULT_PRESENTATION_POLICY_VERSION
        ),
        presentation_policy_checksum=request.project.presentation_policy_checksum,
        template_version=request.project.template_version,
        renderer_contract_version=RENDERER_CONTRACT_VERSION,
        exporter_contract_version=EXPORTER_CONTRACT_VERSION,
        source_lock_version=request.source_lock_version,
        expected_slide_numbers=expected,
        pt_source_hash=compute_slides_fingerprint(request.slides),
        en_source_hash=compute_slides_fingerprint(request.slides),
        raw_image_hashes=collect_raw_images(request, staging_dir),
        avatar_hash=creator_asset_hash(request.project),
        standard_slides_pt=collect_standard_slides(staging_dir / LANGUAGE_PT, expected),
        standard_slides_en=collect_standard_slides(staging_dir / LANGUAGE_EN, expected),
        hd_slides_pt=collect_hd_slides(staging_dir / LANGUAGE_PT, expected),
        hd_slides_en=collect_hd_slides(staging_dir / LANGUAGE_EN, expected),
        pdfs=collect_pdfs(staging_dir, expected),
    )


def collect_raw_images(
    request: ArtifactBuildRequest,
    staging_dir: Path,
) -> tuple[ArtifactRawImageEntry, ...]:
    if not request.project.generate_images:
        return ()
    images_dir = staging_dir / SHARED_IMAGES_DIR_NAME
    entries: list[ArtifactRawImageEntry] = []
    for slide in request.slides:
        filename = _SLIDE_FILENAME_TEMPLATE.format(slide.slide_number)
        path = images_dir / filename
        if not path.is_file():
            continue
        entries.append(
            ArtifactRawImageEntry(
                slide_number=slide.slide_number,
                relative_path=f"{SHARED_IMAGES_DIR_NAME}/{filename}",
                sha256=sha256_file(path),
            )
        )
    return tuple(entries)


def collect_standard_slides(
    language_dir: Path,
    expected: Sequence[int],
) -> tuple[ArtifactSlideFileEntry, ...]:
    return collect_rendered_slides(language_dir, expected, hd=False)


def collect_hd_slides(
    language_dir: Path,
    expected: Sequence[int],
) -> tuple[ArtifactSlideFileEntry, ...]:
    return collect_rendered_slides(language_dir, expected, hd=True)


def collect_rendered_slides(
    language_dir: Path,
    expected: Sequence[int],
    *,
    hd: bool,
) -> tuple[ArtifactSlideFileEntry, ...]:
    entries: list[ArtifactSlideFileEntry] = []
    for slide_number in expected:
        filename = _SLIDE_FILENAME_TEMPLATE.format(slide_number)
        relative = f"{HD_SUBDIR_NAME}/{filename}" if hd else filename
        path = language_dir / relative
        if not path.is_file():
            raise ValueError(ERR_ARTIFACT_STAGING_INCOMPLETE)
        width, height = image_dimensions(path)
        entries.append(
            ArtifactSlideFileEntry(
                slide_number=slide_number,
                relative_path=f"{language_dir.name}/{relative}",
                sha256=sha256_file(path),
                width=width,
                height=height,
            )
        )
    return tuple(entries)


def collect_pdfs(
    staging_dir: Path,
    expected: Sequence[int],
) -> tuple[ArtifactPdfEntry, ...]:
    entries: list[ArtifactPdfEntry] = []
    for language in (LANGUAGE_PT, LANGUAGE_EN):
        pdf_path = staging_dir / language / _PDF_FILENAME
        if not pdf_path.is_file():
            continue
        entries.append(
            ArtifactPdfEntry(
                language=language,
                relative_path=f"{language}/{_PDF_FILENAME}",
                page_count=pdf_page_count(pdf_path),
                sha256=sha256_file(pdf_path),
            )
        )
    if entries and entries[0].page_count != len(expected):
        raise ValueError(ERR_ARTIFACT_STAGING_INCOMPLETE)
    return tuple(entries)


def ensure_promoted(staging_dir: Path, version_dir: Path) -> None:
    if not promote_staging(staging_dir, version_dir):
        raise ValueError(ERR_ARTIFACT_STAGING_INCOMPLETE)


def promote_staging(staging_dir: Path, version_dir: Path) -> bool:
    if version_dir.exists():
        return version_dir.is_dir()
    version_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir.replace(version_dir)
    return version_dir.is_dir()


def write_manifest(path: Path, manifest: CarouselArtifactManifest) -> None:
    path.write_text(
        json.dumps(manifest.to_payload(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_current_index(project_root: Path, artifact_version: str) -> None:
    payload = {
        "artifact_version": artifact_version,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    target = project_root / ARTIFACT_CURRENT_INDEX_FILENAME
    temp_path = target.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(target)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int]:
    from PIL import Image as PILImage

    with PILImage.open(path) as image:
        return int(image.size[0]), int(image.size[1])


def pdf_page_count(path: Path) -> int:
    try:
        return len(PdfReader(str(path)).pages)
    except (OSError, ValueError, PyPdfError) as exc:
        raise ValueError(ERR_ARTIFACT_STAGING_INCOMPLETE) from exc


__all__ = [
    "build_manifest",
    "collect_hd_slides",
    "collect_pdfs",
    "collect_raw_images",
    "collect_rendered_slides",
    "collect_standard_slides",
    "creator_asset_hash",
    "ensure_promoted",
    "image_dimensions",
    "pdf_page_count",
    "populate_staging",
    "promote_staging",
    "sha256_file",
    "sha256_text",
    "version_input_from_request",
    "write_current_index",
    "write_manifest",
]
