"""Unit tests for carousel artifact build service.

Feature: Versioned carousel presentation contract

  Scenario: Deterministic artifact version for unchanged inputs
    Given the same canonical build inputs
    When artifact_version is computed twice
    Then both values match

  Scenario: Concurrent refinement loses optimistic lock and cannot promote
    Given two refinements start from the same lock version
    When the first candidate activates successfully
    Then the second compare-and-swap returns a conflict
    And the first artifact remains active
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from PIL import Image as PILImage
from pypdf import PdfWriter

from rag_backend.application.services.carousel.artifact_build_service import (
    CarouselArtifactBuildService,
)
from rag_backend.application.services.carousel.artifact_build_types import (
    ArtifactBuildRequest,
    ArtifactBuildResult,
    ArtifactVersionInput,
    compute_artifact_version,
    compute_operation_id,
    compute_slides_fingerprint,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
)
from rag_backend.domain.constants.artifact_build import (
    ARTIFACT_MANIFEST_FILENAME,
    ARTIFACT_VERSION_PREFIX,
    ARTIFACT_VERSIONS_DIR,
    ERR_ARTIFACT_BUILD_CONFLICT,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide


def _make_project(tmp_path: Path, **overrides: object) -> CarouselProject:
    defaults: dict[str, object] = {
        "topic": "topic",
        "audience": "audience",
        "niche": "niche",
        "output_dir": str(tmp_path),
        "presentation_policy_version": "hero_lower_third_v1",
        "presentation_policy_checksum": "sha256-abc",
        "template_version": "v2",
    }
    defaults.update(overrides)
    return CarouselProject(**defaults)


def _make_slide(slide_number: int, project_id: uuid4 | None = None) -> CarouselSlide:
    return CarouselSlide(
        project_id=project_id or uuid4(),
        slide_number=slide_number,
        slide_type="content",
        heading=f"Heading {slide_number}",
        body=f"Body {slide_number}",
    )


def _write_jpeg(path: Path, width: int = 1080, height: int = 1350) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.new("RGB", (width, height)).save(path, format="JPEG")


def _write_pdf(path: Path, pages: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def _populate_legacy_output(project_root: Path, slide_numbers: list[int]) -> None:
    for language in (LANGUAGE_PT, LANGUAGE_EN):
        for slide_number in slide_numbers:
            _write_jpeg(project_root / language / f"slide_{slide_number}.jpg")
            _write_jpeg(
                project_root / language / HD_SUBDIR_NAME / f"slide_{slide_number}.jpg",
                width=2160,
                height=2700,
            )
        _write_pdf(project_root / language / "carousel.pdf", len(slide_numbers))


@pytest.mark.unit
class TestArtifactVersionComputation:
    def test_compute_artifact_version_is_deterministic(self) -> None:
        project_id = str(uuid4())
        inputs = ArtifactVersionInput(
            project_id=project_id,
            source_lock_version=2,
            presentation_policy_version="hero_lower_third_v1",
            presentation_policy_checksum="sha256-abc",
            template_version="v2",
            slides_fingerprint="slides-hash",
            design_fingerprint="design-hash",
            creator_asset_hash=None,
            export_width=1080,
            export_height=1350,
        )
        first = compute_artifact_version(inputs)
        second = compute_artifact_version(inputs)
        assert first == second
        assert first.startswith(ARTIFACT_VERSION_PREFIX)
        assert len(first.removeprefix(ARTIFACT_VERSION_PREFIX)) == 64

    def test_compute_operation_id_is_deterministic(self) -> None:
        project_id = str(uuid4())
        version = f"{ARTIFACT_VERSION_PREFIX}{'a' * 64}"
        first = compute_operation_id(project_id, 2, version)
        second = compute_operation_id(project_id, 2, version)
        assert first == second
        assert len(first) == 64

    def test_compute_slides_fingerprint_changes_with_copy(self) -> None:
        project_id = uuid4()
        slides = [_make_slide(1, project_id), _make_slide(2, project_id)]
        first = compute_slides_fingerprint(slides)
        slides[0] = CarouselSlide(
            project_id=project_id,
            slide_number=1,
            slide_type="content",
            heading="Changed",
            body="Body 1",
        )
        second = compute_slides_fingerprint(slides)
        assert first != second


@pytest.mark.asyncio
@pytest.mark.unit
class TestCarouselArtifactBuildService:
    async def test_build_and_activate_promotes_version_directory(
        self,
        tmp_path: Path,
    ) -> None:
        project = _make_project(tmp_path)
        slides = [_make_slide(1, project.id), _make_slide(2, project.id)]
        _populate_legacy_output(tmp_path, [1, 2])

        db = AsyncMock()
        build_repo = MagicMock()
        build_repo.get_by_project_and_version = AsyncMock(return_value=None)
        build_repo.upsert_build = AsyncMock(side_effect=lambda build: build)
        build_repo.activate_build = AsyncMock(return_value=3)

        service = CarouselArtifactBuildService()
        with patch(
            "rag_backend.application.services.carousel.artifact_build_service.PostgresCarouselArtifactBuildRepository",
            return_value=build_repo,
        ):
            result = await service.build_and_activate(
                db,
                ArtifactBuildRequest(
                    project=project,
                    slides=slides,
                    source_lock_version=2,
                    prior_artifact_version=None,
                ),
            )

        assert isinstance(result, ArtifactBuildResult)
        assert result.artifact_version.startswith(ARTIFACT_VERSION_PREFIX)
        version_dir = tmp_path / ARTIFACT_VERSIONS_DIR / result.artifact_version
        assert version_dir.is_dir()
        assert (version_dir / ARTIFACT_MANIFEST_FILENAME).is_file()
        assert (version_dir / LANGUAGE_PT / "slide_1.jpg").is_file()
        db.commit.assert_awaited()

    async def test_build_and_activate_returns_conflict_on_losing_cas(
        self,
        tmp_path: Path,
    ) -> None:
        project = _make_project(tmp_path)
        slides = [_make_slide(1, project.id)]
        _populate_legacy_output(tmp_path, [1])

        db = AsyncMock()
        build_repo = MagicMock()
        build_repo.get_by_project_and_version = AsyncMock(return_value=None)
        build_repo.upsert_build = AsyncMock()
        build_repo.mark_build_status = AsyncMock()
        build_repo.activate_build = AsyncMock(
            side_effect=ValueError(ERR_ARTIFACT_BUILD_CONFLICT)
        )

        service = CarouselArtifactBuildService()
        with patch(
            "rag_backend.application.services.carousel.artifact_build_service.PostgresCarouselArtifactBuildRepository",
            return_value=build_repo,
        ):
            result = await service.build_and_activate(
                db,
                ArtifactBuildRequest(
                    project=project,
                    slides=slides,
                    source_lock_version=2,
                    prior_artifact_version=None,
                ),
            )

        from rag_backend.application.services.carousel.artifact_build_service import (
            ArtifactBuildFailure,
        )

        assert isinstance(result, ArtifactBuildFailure)
        assert ERR_ARTIFACT_BUILD_CONFLICT in result.errors

    async def test_reuses_existing_valid_version_without_restaging(
        self,
        tmp_path: Path,
    ) -> None:
        project = _make_project(tmp_path)
        slides = [_make_slide(1, project.id)]
        _populate_legacy_output(tmp_path, [1])

        version_input = ArtifactVersionInput(
            project_id=str(project.id),
            source_lock_version=2,
            presentation_policy_version="hero_lower_third_v1",
            presentation_policy_checksum="sha256-abc",
            template_version="v2",
            slides_fingerprint=compute_slides_fingerprint(slides),
            design_fingerprint=None,
            creator_asset_hash=None,
            export_width=1080,
            export_height=1350,
        )
        artifact_version = compute_artifact_version(version_input)
        version_dir = tmp_path / ARTIFACT_VERSIONS_DIR / artifact_version
        version_dir.mkdir(parents=True)
        (version_dir / ARTIFACT_MANIFEST_FILENAME).write_text("{}", encoding="utf-8")

        db = AsyncMock()
        build_repo = MagicMock()
        build_repo.get_by_project_and_version = AsyncMock(
            return_value=MagicMock(
                project_id=project.id, artifact_version=artifact_version
            )
        )
        build_repo.activate_build = AsyncMock(return_value=3)

        service = CarouselArtifactBuildService()
        with patch(
            "rag_backend.application.services.carousel.artifact_build_service.PostgresCarouselArtifactBuildRepository",
            return_value=build_repo,
        ):
            result = await service.build_and_activate(
                db,
                ArtifactBuildRequest(
                    project=project,
                    slides=slides,
                    source_lock_version=2,
                    prior_artifact_version=None,
                ),
            )

        assert isinstance(result, ArtifactBuildResult)
        assert result.artifact_version == artifact_version
        assert result.lock_version == 3
        build_repo.activate_build.assert_awaited_once()
