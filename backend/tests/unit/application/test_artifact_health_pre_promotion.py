"""Pre-promotion artifact health validation (AE-0313).

Feature: Republish a completed carousel's artifacts
  Scenario: Health check validates fresh outputs, not the old version root
    (see tests/features/carousel_republish.feature)

Reproduces the prod 66014ba3 false negative: a completed, versioned project is
re-rendered into the PLAIN project-root pt/ en/ dirs, but the health check
resolved against the OLD versioned serving root and reported "pt PDF missing".
``validate_pre_promotion=True`` validates the freshly rendered project-root
outputs instead.

Call-site matrix (cold-critic r6): every (validate_pre_promotion x
artifact_version state: NULL / set / stale-from-partial-run) combination is
covered so the shared health-check change is proven safe for BOTH the republish
path and the primary images-approval finalize.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image as PILImage
from pypdf import PdfWriter

from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthRequest,
    evaluate_carousel_artifacts,
)
from rag_backend.domain.constants import (
    CAROUSEL_HEIGHT,
    CAROUSEL_WIDTH,
    HD_SUBDIR_NAME,
    LANGUAGE_PT,
)
from rag_backend.domain.constants.artifact_build import ARTIFACT_VERSIONS_DIR
from rag_backend.domain.models import CarouselProject, CarouselSlide

_PDF_MISSING_FRAGMENT = "PDF missing"
_MANIFEST_FRAGMENT = "manifest"


def _write_jpeg(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.new("RGB", (width, height)).save(path, format="JPEG")


def _write_pdf(path: Path, pages: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def _populate_language(root: Path, slide_numbers: list[int]) -> None:
    for slide_number in slide_numbers:
        _write_jpeg(
            root / LANGUAGE_PT / f"slide_{slide_number}.jpg",
            CAROUSEL_WIDTH,
            CAROUSEL_HEIGHT,
        )
        _write_jpeg(
            root / LANGUAGE_PT / HD_SUBDIR_NAME / f"slide_{slide_number}.jpg",
            CAROUSEL_WIDTH * 2,
            CAROUSEL_HEIGHT * 2,
        )
    _write_pdf(root / LANGUAGE_PT / "carousel.pdf", len(slide_numbers))


def _make_slides(project_id: object, count: int) -> list[CarouselSlide]:
    return [
        CarouselSlide(
            project_id=project_id,
            slide_number=n,
            slide_type="content",
            heading=f"H{n}",
            body=f"B{n}",
        )
        for n in range(1, count + 1)
    ]


def _project(tmp_path: Path, *, artifact_version: str | None) -> CarouselProject:
    project = CarouselProject(
        topic="t",
        audience="a",
        niche="n",
        output_dir=str(tmp_path),
        generate_images=False,
    )
    project.artifact_version = artifact_version
    # Fresh render points the PDF pointer at the PLAIN project-root path (this is
    # exactly what CarouselRefinementService.re_render_slides writes).
    project.pdf_path = str(tmp_path / LANGUAGE_PT / "carousel.pdf")
    return project


def _request(
    project: CarouselProject,
    slides: list[CarouselSlide],
    *,
    pre_promotion: bool,
) -> CarouselArtifactHealthRequest:
    return CarouselArtifactHealthRequest(
        project=project,
        slides=slides,
        require_english=False,
        validate_pre_promotion=pre_promotion,
    )


@pytest.mark.unit
class TestPrePromotionHealth:
    def test_versioned_project_fresh_outputs_pass_pre_promotion(
        self, tmp_path: Path
    ) -> None:
        """66014ba3 regression: fresh plain-root PDFs are NOT reported missing."""
        version = "sha256-" + "a" * 64
        (tmp_path / ARTIFACT_VERSIONS_DIR / version).mkdir(parents=True)
        project = _project(tmp_path, artifact_version=version)
        slides = _make_slides(project.id, 2)
        _populate_language(tmp_path, [1, 2])

        report = evaluate_carousel_artifacts(
            _request(project, slides, pre_promotion=True)
        )

        assert report.ok, report.errors

    def test_versioned_project_fresh_outputs_fail_without_pre_promotion(
        self, tmp_path: Path
    ) -> None:
        """The OLD behavior: validating the empty version root false-negatives."""
        version = "sha256-" + "b" * 64
        (tmp_path / ARTIFACT_VERSIONS_DIR / version).mkdir(parents=True)
        project = _project(tmp_path, artifact_version=version)
        slides = _make_slides(project.id, 2)
        _populate_language(tmp_path, [1, 2])

        report = evaluate_carousel_artifacts(
            _request(project, slides, pre_promotion=False)
        )

        assert not report.ok
        assert any(_PDF_MISSING_FRAGMENT in error for error in report.errors)

    def test_null_version_passes_both_modes(self, tmp_path: Path) -> None:
        """artifact_version NULL: serving root == project root either way."""
        project = _project(tmp_path, artifact_version=None)
        slides = _make_slides(project.id, 2)
        _populate_language(tmp_path, [1, 2])

        for pre_promotion in (True, False):
            report = evaluate_carousel_artifacts(
                _request(project, slides, pre_promotion=pre_promotion)
            )
            assert report.ok, (pre_promotion, report.errors)

    def test_stale_version_pre_promotion_skips_manifest(self, tmp_path: Path) -> None:
        """Stale artifact_version from a partial run (no version dir on disk).

        First-time-finalize regression: pre-promotion validates the fresh
        project-root outputs and skips the stale-version manifest check.
        """
        project = _project(tmp_path, artifact_version="sha256-" + "c" * 64)
        slides = _make_slides(project.id, 2)
        _populate_language(tmp_path, [1, 2])

        report = evaluate_carousel_artifacts(
            _request(project, slides, pre_promotion=True)
        )

        assert report.ok, report.errors

    def test_stale_version_without_pre_promotion_flags_manifest(
        self, tmp_path: Path
    ) -> None:
        """Same stale state WITHOUT the flag still enforces the manifest check."""
        project = _project(tmp_path, artifact_version="sha256-" + "d" * 64)
        slides = _make_slides(project.id, 2)
        _populate_language(tmp_path, [1, 2])

        report = evaluate_carousel_artifacts(
            _request(project, slides, pre_promotion=False)
        )

        assert not report.ok
        assert any(_MANIFEST_FRAGMENT in error.lower() for error in report.errors)
