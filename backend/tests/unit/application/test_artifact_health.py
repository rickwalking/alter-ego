"""Unit tests for carousel artifact health validation.

Feature: Carousel artifact health gate

  Scenario: Missing HD slide blocks publish
    Given a seven-slide carousel has standard PT and EN renders
    And PT HD slide 7 is missing
    When artifact health is evaluated
    Then the report includes an HD missing error

  Scenario: CTA without raw image passes when rendered outputs exist
    Given a seven-slide carousel has no raw image for the CTA slide
    And all rendered PT and EN slides exist
    And both PDFs have seven pages
    When artifact health is evaluated
    Then the report passes

  Scenario: Missing output_dir fails health
    Given a carousel project with no output_dir
    When artifact health is evaluated
    Then the report fails with missing output_dir

  Scenario: Missing PT rendered slides fail health
    Given a carousel with slides but no PT rendered directory
    When artifact health is evaluated
    Then the report fails with missing rendered slides

  Scenario: CTA slides are excluded from raw image validation
    Given a carousel with a CTA slide that has no image_path
    When raw image validation runs
    Then CTA is not flagged as missing a raw image
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.artifact_health import (
    CarouselArtifactHealthRequest,
    ImageDimensions,
    JpegCheck,
    PdfCheck,
    PdfCheckRequest,
    _dimension_errors,
    _expected_slide_numbers,
    _number_from_path,
    _pdf_check,
    _requires_english,
    _resolved_output_dir,
    _safe_output_file,
    _slide_filename,
    _slide_numbers,
    _validate_hd_slide,
    _validate_jpeg,
    _validate_language,
    _validate_pdf,
    _validate_raw_images,
    _validate_rendered_slide,
    evaluate_carousel_artifacts,
    format_artifact_health_errors,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide


def _make_project(**overrides: object) -> CarouselProject:
    defaults: dict[str, object] = {
        "topic": "test",
        "audience": "test",
        "niche": "test",
        "output_dir": "/tmp/test_output",
    }
    defaults.update(overrides)
    return CarouselProject(**defaults)


def _make_slide(
    slide_number: int = 1,
    slide_type: str = SLIDE_TYPE_CONTENT,
    project_id: uuid4 | None = None,
    **extras: object,
) -> CarouselSlide:
    pid = project_id or uuid4()
    return CarouselSlide(
        project_id=pid,
        slide_number=slide_number,
        slide_type=slide_type,
        heading="test",
        body="test",
        **extras,
    )


@pytest.mark.unit
class TestEvaluateCarouselArtifacts:
    def test_missing_output_dir_fails(self) -> None:
        project = _make_project(output_dir=None)
        request = CarouselArtifactHealthRequest(project=project, slides=[])
        report = evaluate_carousel_artifacts(request)
        assert not report.ok
        assert any("missing" in e.lower() for e in report.errors)

    def test_nonexistent_output_dir_fails(self) -> None:
        project = _make_project(output_dir="/nonexistent/path/12345")
        request = CarouselArtifactHealthRequest(project=project, slides=[])
        report = evaluate_carousel_artifacts(request)
        assert not report.ok

    def test_no_slides_fails(self) -> None:
        project = _make_project()
        request = CarouselArtifactHealthRequest(project=project, slides=[])
        report = evaluate_carousel_artifacts(request)
        assert not report.ok
        assert report.errors  # has at least one error

    def test_cta_excluded_from_raw_image_validation(self) -> None:
        project = _make_project(generate_images=True)
        slides = [
            _make_slide(
                slide_number=1, slide_type=SLIDE_TYPE_INTRO, image_prompt="scene 1"
            ),
            _make_slide(slide_number=7, slide_type=SLIDE_TYPE_CTA),
        ]
        request = CarouselArtifactHealthRequest(project=project, slides=slides)
        errors = _validate_raw_images(request, Path("/tmp"))
        cta_errors = [e for e in errors if "7" in e and "raw" in e.lower()]
        assert cta_errors == []


@pytest.mark.unit
class TestValidateJpeg:
    def test_valid_jpeg_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (1080, 1350)).save(file_path, format="JPEG")
        check = JpegCheck(
            path=file_path, label=str(file_path), expected_dimensions=None
        )
        result = _validate_jpeg(check)
        assert result == []

    def test_tiny_file_fails(self, tmp_path: Path) -> None:
        tiny_file = tmp_path / "slide_1.jpg"
        tiny_file.write_bytes(b"not a jpeg")
        check = JpegCheck(path=tiny_file, label="test", expected_dimensions=None)
        result = _validate_jpeg(check)
        assert len(result) > 0

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.jpg"
        check = JpegCheck(path=missing, label="test", expected_dimensions=None)
        result = _validate_jpeg(check)
        assert len(result) > 0

    def test_wrong_dimensions_fails(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (800, 600)).save(file_path, format="JPEG", quality=95)
        check = JpegCheck(
            path=file_path,
            label="test",
            expected_dimensions=ImageDimensions(1080, 1350),
        )
        result = _validate_jpeg(check)
        assert len(result) > 0
        assert any("dimensions" in e.lower() for e in result)

    def test_correct_dimensions_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        file_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (1080, 1350)).save(file_path, format="JPEG")
        check = JpegCheck(
            path=file_path,
            label="test",
            expected_dimensions=ImageDimensions(1080, 1350),
        )
        result = _validate_jpeg(check)
        assert result == []


@pytest.mark.unit
class TestValidatePdfs:
    def test_missing_pdf_returns_error(self) -> None:
        project = _make_project()
        slides = [_make_slide()]
        request = CarouselArtifactHealthRequest(project=project, slides=slides)
        check = PdfCheck(
            path=Path("/nonexistent/path.pdf"), label="pt", expected_pages=7
        )
        result = _validate_pdf(check)
        assert any("missing" in e.lower() for e in result)

    def test_wrong_page_count_fails(self, tmp_path: Path) -> None:
        from pypdf import PdfWriter

        pdf_path = tmp_path / "carousel.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=1080, height=1350)
        writer.add_blank_page(width=1080, height=1350)
        with pdf_path.open("wb") as f:
            writer.write(f)
        check = PdfCheck(path=pdf_path, label="pt", expected_pages=7)
        result = _validate_pdf(check)
        assert any("page count" in e.lower() for e in result)

    def test_correct_page_count_passes(self, tmp_path: Path) -> None:
        from pypdf import PdfWriter

        pdf_path = tmp_path / "carousel.pdf"
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=1080, height=1350)
        with pdf_path.open("wb") as f:
            writer.write(f)
        check = PdfCheck(path=pdf_path, label="pt", expected_pages=3)
        result = _validate_pdf(check)
        assert result == []


@pytest.mark.unit
class TestSlideNumbers:
    def test_slide_filename_format(self) -> None:
        assert _slide_filename(1) == f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}"
        assert _slide_filename(7) == f"{SLIDE_FILENAME_PREFIX}7{SLIDE_IMAGE_EXTENSION}"

    def test_number_from_path(self) -> None:
        path = Path(f"/tmp/pt/{SLIDE_FILENAME_PREFIX}3{SLIDE_IMAGE_EXTENSION}")
        assert _number_from_path(path) == 3

    def test_slide_numbers_from_directory(self, tmp_path: Path) -> None:
        pt_dir = tmp_path / LANGUAGE_PT
        pt_dir.mkdir()
        for i in (1, 3, 5):
            (pt_dir / f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}").write_bytes(
                b"\xff\xd8\xff\xe0" + b"\x00" * 100
            )
        result = _slide_numbers(pt_dir)
        assert result == (1, 3, 5)

    def test_slide_numbers_empty_dir(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _slide_numbers(empty_dir)
        assert result == ()

    def test_slide_numbers_nonexistent_dir(self) -> None:
        result = _slide_numbers(Path("/nonexistent"))
        assert result == ()


@pytest.mark.unit
class TestRequiresEnglish:
    def test_explicit_require_true(self) -> None:
        project = _make_project()
        slide = _make_slide()
        request = CarouselArtifactHealthRequest(
            project=project, slides=[slide], require_english=True
        )
        assert _requires_english(request) is True

    def test_explicit_require_false(self) -> None:
        project = _make_project()
        slide = _make_slide()
        request = CarouselArtifactHealthRequest(
            project=project, slides=[slide], require_english=False
        )
        assert _requires_english(request) is False

    def test_auto_detect_with_en_translation(self) -> None:
        project = _make_project()
        slide = _make_slide(
            extras={"translation_en": {"heading": "EN heading", "body": "EN body"}},
        )
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        assert _requires_english(request) is True

    def test_auto_detect_without_en_translation(self) -> None:
        project = _make_project()
        slide = _make_slide()
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        assert _requires_english(request) is False


@pytest.mark.unit
class TestExpectedSlideNumbers:
    def test_deduplicates_and_sorts(self) -> None:
        slides = [
            _make_slide(slide_number=3),
            _make_slide(slide_number=1),
            _make_slide(slide_number=3),
        ]
        result = _expected_slide_numbers(slides)
        assert result == (1, 3)

    def test_empty_returns_empty(self) -> None:
        assert _expected_slide_numbers([]) == ()


@pytest.mark.unit
class TestDimensionErrors:
    def test_no_errors_when_none_expected(self) -> None:
        check = JpegCheck(
            path=Path("/tmp/test.jpg"), label="test", expected_dimensions=None
        )
        result = _dimension_errors(check, ImageDimensions(100, 200))
        assert result == []

    def test_no_errors_when_matching(self) -> None:
        check = JpegCheck(
            path=Path("/tmp/test.jpg"),
            label="test",
            expected_dimensions=ImageDimensions(1080, 1350),
        )
        result = _dimension_errors(check, ImageDimensions(1080, 1350))
        assert result == []

    def test_error_when_mismatch(self) -> None:
        check = JpegCheck(
            path=Path("/tmp/test.jpg"),
            label="test",
            expected_dimensions=ImageDimensions(1080, 1350),
        )
        result = _dimension_errors(check, ImageDimensions(100, 200))
        assert len(result) == 1
        assert "dimensions" in result[0].lower()


@pytest.mark.unit
class TestFormatArtifactHealthErrors:
    def test_formats_errors(self) -> None:
        errors = ("missing slide_1.jpg", "missing slide_2.jpg")
        result = format_artifact_health_errors(errors)
        assert result == "missing slide_1.jpg; missing slide_2.jpg"

    def test_default_message_when_empty(self) -> None:
        result = format_artifact_health_errors(())
        assert "incomplete" in result.lower()


@pytest.mark.unit
class TestResolvedOutputDir:
    def test_returns_none_when_output_dir_is_none(self) -> None:
        project = _make_project(output_dir=None)
        assert _resolved_output_dir(project) is None

    def test_returns_resolved_path(self) -> None:
        project = _make_project(output_dir="/tmp/test_output")
        result = _resolved_output_dir(project)
        assert result is not None
        assert str(result).endswith("test_output")


@pytest.mark.unit
class TestNumberFromPath:
    def test_extracts_number(self) -> None:
        path = Path(f"/tmp/{SLIDE_FILENAME_PREFIX}5{SLIDE_IMAGE_EXTENSION}")
        assert _number_from_path(path) == 5

    def test_returns_zero_for_non_digit_stem(self) -> None:
        path = Path("/tmp/slide_abc.jpg")
        assert _number_from_path(path) == 0


@pytest.mark.unit
class TestValidateRenderedSlide:
    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        path = (
            tmp_path / LANGUAGE_PT / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}"
        )
        result = _validate_rendered_slide(
            path, LANGUAGE_PT, ImageDimensions(1080, 1350)
        )
        assert len(result) == 1
        assert "missing" in result[0].lower()

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        pt_dir = tmp_path / LANGUAGE_PT
        pt_dir.mkdir()
        file_path = pt_dir / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}"
        PILImage.new("RGB", (1080, 1350)).save(file_path, format="JPEG")
        result = _validate_rendered_slide(
            file_path, LANGUAGE_PT, ImageDimensions(1080, 1350)
        )
        assert result == []


@pytest.mark.unit
class TestValidateHdSlide:
    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        path = (
            tmp_path
            / LANGUAGE_PT
            / HD_SUBDIR_NAME
            / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}"
        )
        result = _validate_hd_slide(path, LANGUAGE_PT, ImageDimensions(2160, 2700))
        assert len(result) == 1
        assert "hd" in result[0].lower()

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        hd_dir = tmp_path / LANGUAGE_PT / HD_SUBDIR_NAME
        hd_dir.mkdir(parents=True)
        file_path = hd_dir / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}"
        PILImage.new("RGB", (2160, 2700)).save(file_path, format="JPEG")
        result = _validate_hd_slide(file_path, LANGUAGE_PT, ImageDimensions(2160, 2700))
        assert result == []


@pytest.mark.unit
class TestValidateLanguage:
    def test_missing_standard_and_hd_slides(self, tmp_path: Path) -> None:
        pt_dir = tmp_path / LANGUAGE_PT
        pt_dir.mkdir()
        errors = _validate_language(tmp_path, LANGUAGE_PT, (1, 2))
        standard_missing = [
            e for e in errors if "rendered slide missing" in e and "HD" not in e
        ]
        hd_missing = [e for e in errors if "HD" in e]
        assert len(standard_missing) == 2
        assert len(hd_missing) == 2

    def test_all_slides_present_no_errors(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        pt_dir = tmp_path / LANGUAGE_PT
        hd_dir = pt_dir / HD_SUBDIR_NAME
        pt_dir.mkdir()
        hd_dir.mkdir()
        for i in (1, 2):
            PILImage.new("RGB", (1080, 1350)).save(
                pt_dir / f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}",
                format="JPEG",
            )
            PILImage.new("RGB", (2160, 2700)).save(
                hd_dir / f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}",
                format="JPEG",
            )
        errors = _validate_language(tmp_path, LANGUAGE_PT, (1, 2))
        assert errors == []


@pytest.mark.unit
class TestValidateRawImages:
    def test_skips_when_generate_images_false(self) -> None:
        project = _make_project(generate_images=False)
        slide = _make_slide(
            slide_number=1, slide_type=SLIDE_TYPE_CONTENT, image_prompt="scene"
        )
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        result = _validate_raw_images(request, Path("/tmp"))
        assert result == []

    def test_flags_missing_image_prompt(self, tmp_path: Path) -> None:
        project = _make_project(output_dir=str(tmp_path), generate_images=True)
        slide = _make_slide(
            slide_number=1, slide_type=SLIDE_TYPE_CONTENT, image_prompt=""
        )
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        result = _validate_raw_images(request, tmp_path)
        assert any("prompt" in e.lower() for e in result)

    def test_flags_missing_raw_file(self, tmp_path: Path) -> None:
        project = _make_project(output_dir=str(tmp_path), generate_images=True)
        slide = _make_slide(
            slide_number=1, slide_type=SLIDE_TYPE_INTRO, image_prompt="scene"
        )
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        result = _validate_raw_images(request, tmp_path)
        assert any("raw" in e.lower() for e in result)

    def test_valid_raw_image_passes(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        project = _make_project(output_dir=str(tmp_path), generate_images=True)
        slide = _make_slide(
            slide_number=1, slide_type=SLIDE_TYPE_INTRO, image_prompt="scene"
        )
        shared_dir = tmp_path / SHARED_IMAGES_DIR_NAME
        shared_dir.mkdir()
        PILImage.new("RGB", (1080, 1350)).save(
            shared_dir / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}",
            format="JPEG",
        )
        request = CarouselArtifactHealthRequest(project=project, slides=[slide])
        result = _validate_raw_images(request, tmp_path)
        assert result == []


@pytest.mark.unit
class TestPdfCheck:
    def test_pdf_path_for_pt_language(self) -> None:
        project = _make_project(pdf_path="/tmp/carousel.pdf")
        request = PdfCheckRequest(
            project=project,
            output_dir=Path("/tmp"),
            language=LANGUAGE_PT,
            pages=7,
        )
        check = _pdf_check(request)
        assert check.label == LANGUAGE_PT
        assert check.expected_pages == 7

    def test_pdf_path_for_en_language_uses_en_path(self) -> None:
        project = _make_project(
            pdf_path="/tmp/carousel.pdf", pdf_path_en="/tmp/carousel_en.pdf"
        )
        request = PdfCheckRequest(
            project=project,
            output_dir=Path("/tmp"),
            language=LANGUAGE_EN,
            pages=7,
        )
        check = _pdf_check(request)
        assert check.label == LANGUAGE_EN

    def test_pdf_path_fallback_when_no_path(self) -> None:
        project = _make_project()
        request = PdfCheckRequest(
            project=project,
            output_dir=Path("/tmp/test_output"),
            language=LANGUAGE_PT,
            pages=3,
        )
        check = _pdf_check(request)
        assert check.expected_pages == 3


@pytest.mark.unit
class TestSafeOutputFile:
    def test_returns_resolved_when_inside_output_dir(self, tmp_path: Path) -> None:
        output_dir = tmp_path.resolve()
        file_path = str(output_dir / "carousel.pdf")
        result = _safe_output_file(output_dir, file_path)
        assert result is not None

    def test_returns_none_when_outside_output_dir(self, tmp_path: Path) -> None:
        output_dir = tmp_path.resolve()
        file_path = "/etc/passwd"
        result = _safe_output_file(output_dir, file_path)
        assert result is None


@pytest.mark.unit
class TestValidatePdf:
    def test_none_path_returns_missing_error(self) -> None:
        check = PdfCheck(path=None, label="pt", expected_pages=1)
        result = _validate_pdf(check)
        assert any("missing" in e.lower() for e in result)

    def test_unreadable_pdf_returns_error(self, tmp_path: Path) -> None:
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"not a pdf at all")
        check = PdfCheck(path=bad_pdf, label="pt", expected_pages=1)
        result = _validate_pdf(check)
        assert len(result) > 0


@pytest.mark.unit
class TestSlideNumbersFilters:
    def test_non_digit_files_are_ignored(self, tmp_path: Path) -> None:
        pt_dir = tmp_path / LANGUAGE_PT
        pt_dir.mkdir()
        (pt_dir / f"{SLIDE_FILENAME_PREFIX}1{SLIDE_IMAGE_EXTENSION}").write_bytes(
            b"\xff\xd8\xff\xe0" + b"\x00" * 100
        )
        (pt_dir / f"{SLIDE_FILENAME_PREFIX}abc{SLIDE_IMAGE_EXTENSION}").write_bytes(
            b"\xff\xd8\xff\xe0" + b"\x00" * 100
        )
        result = _slide_numbers(pt_dir)
        assert result == (1,)


@pytest.mark.unit
class TestEvaluateIntegration:
    def test_full_pass_with_pt_only(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        project = _make_project(output_dir=str(tmp_path))
        pt_dir = tmp_path / LANGUAGE_PT
        hd_dir = pt_dir / HD_SUBDIR_NAME
        pt_dir.mkdir()
        hd_dir.mkdir()
        for i in range(1, 4):
            PILImage.new("RGB", (1080, 1350)).save(
                pt_dir / f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}",
                format="JPEG",
            )
            PILImage.new("RGB", (2160, 2700)).save(
                hd_dir / f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}",
                format="JPEG",
            )
        slides = [
            _make_slide(slide_number=i, slide_type=SLIDE_TYPE_CONTENT)
            for i in range(1, 4)
        ]
        request = CarouselArtifactHealthRequest(
            project=project, slides=slides, require_english=False
        )
        report = evaluate_carousel_artifacts(request)
        rendered_errors = [e for e in report.errors if "rendered" in e.lower()]
        assert rendered_errors == []

    def test_full_fail_with_missing_renders(self, tmp_path: Path) -> None:
        project = _make_project(output_dir=str(tmp_path))
        (tmp_path / LANGUAGE_PT).mkdir()
        slides = [_make_slide(slide_number=1)]
        request = CarouselArtifactHealthRequest(
            project=project, slides=slides, require_english=False
        )
        report = evaluate_carousel_artifacts(request)
        assert not report.ok
        assert any("missing" in e.lower() for e in report.errors)
