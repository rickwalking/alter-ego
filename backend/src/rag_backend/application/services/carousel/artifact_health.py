"""Carousel artifact health checks for publish-ready workflows."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from rag_backend.application.services.carousel.artifact_manifest import (
    CarouselArtifactManifestPayload,
    manifest_from_payload,
)
from rag_backend.application.services.carousel.artifact_path_resolver import (
    ArtifactServingPaths,
    resolve_and_reconcile_serving_paths,
    resolve_manifest_path,
)
from rag_backend.application.services.carousel.image_validation import (
    is_valid_jpeg,
)
from rag_backend.application.services.carousel.nodes.images import (
    IMAGE_SLIDE_TYPES,
    filter_image_slides,
)
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.domain.constants import (
    CAROUSEL_HEIGHT,
    CAROUSEL_WIDTH,
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
    SHARED_IMAGES_DIR_NAME,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
)
from rag_backend.domain.constants.artifact_build import (
    ERR_ARTIFACT_MANIFEST_INVALID,
    ERR_ARTIFACT_MANIFEST_MISSING,
    ERR_ARTIFACT_MANIFEST_POLICY_MISMATCH,
    ERR_ARTIFACT_MANIFEST_VERSION_MISMATCH,
)
from rag_backend.domain.models import CarouselProject, CarouselSlide

_MIN_JPEG_BYTES = 1024
_PDF_FILENAME = "carousel.pdf"
_MISSING_OUTPUT_DIR = "carousel output_dir is missing"
_OUTPUT_DIR_NOT_FOUND = "carousel output_dir does not exist: {}"
_NO_SLIDES = "carousel has no persisted slides"
_MISSING_RENDER = "{} rendered slide missing: slide_{}.jpg"
_MISSING_HD_RENDER = "{} HD rendered slide missing: slide_{}.jpg"
_MISSING_RAW_IMAGE = "raw generated image missing: slide_{}.jpg"
_MISSING_IMAGE_PROMPT = "image prompt missing for image slide {}"
_MISSING_PDF = "{} PDF missing"
_WRONG_PDF_PAGES = "{} PDF page count {} does not match expected {}"
_INVALID_JPEG = "{} is not a valid JPEG"
_TINY_JPEG = "{} is too small to be a valid generated slide"
_WRONG_DIMENSIONS = "{} dimensions {}x{} do not match expected {}x{}"
_PDF_UNREADABLE = "{} PDF could not be read: {}"


@dataclass(frozen=True)
class ImageDimensions:
    width: int
    height: int


@dataclass(frozen=True)
class CarouselArtifactHealthRequest:
    project: CarouselProject
    slides: Sequence[CarouselSlide]
    require_english: bool | None = None
    # AE-0313: validate the FRESHLY RENDERED pre-promotion outputs under the
    # project root (plain ``pt/`` / ``en/`` dirs) instead of the currently
    # active versioned serving root. The finalize/republish pipeline re-renders
    # into the project root BEFORE the artifact build promotes a new version;
    # validating the old version root would false-negative the fresh PDFs as
    # missing (the 66014ba3 incident) and skip the stale-version manifest check.
    validate_pre_promotion: bool = False


@dataclass(frozen=True)
class CarouselArtifactHealthReport:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    rendered_slide_numbers_pt: tuple[int, ...]
    rendered_slide_numbers_en: tuple[int, ...]


@dataclass(frozen=True)
class JpegCheck:
    path: Path
    label: str
    expected_dimensions: ImageDimensions | None


@dataclass(frozen=True)
class PdfCheck:
    path: Path | None
    label: str
    expected_pages: int


@dataclass(frozen=True)
class ReportInput:
    errors: tuple[str, ...]
    warnings: Sequence[str]
    rendered_pt: tuple[int, ...]
    rendered_en: tuple[int, ...]


@dataclass(frozen=True)
class PdfCheckRequest:
    project: CarouselProject
    output_dir: Path
    language: str
    pages: int


def evaluate_carousel_artifacts(
    request: CarouselArtifactHealthRequest,
) -> CarouselArtifactHealthReport:
    """Validate all files needed before final review, publish, or Instagram."""
    serving_paths = resolve_and_reconcile_serving_paths(request.project)
    output_dir = _health_root(
        serving_paths, validate_pre_promotion=request.validate_pre_promotion
    )
    expected = _expected_slide_numbers(request.slides)
    warnings: list[str] = []
    if output_dir is None:
        return _report(
            ReportInput(
                errors=(_MISSING_OUTPUT_DIR,),
                warnings=warnings,
                rendered_pt=(),
                rendered_en=(),
            )
        )
    if not output_dir.is_dir():
        error = _OUTPUT_DIR_NOT_FOUND.format(output_dir)
        return _report(
            ReportInput(
                errors=(error,),
                warnings=warnings,
                rendered_pt=(),
                rendered_en=(),
            )
        )
    if not expected:
        return _report(
            ReportInput(
                errors=(_NO_SLIDES,),
                warnings=warnings,
                rendered_pt=(),
                rendered_en=(),
            )
        )

    errors = _validate_language(output_dir, LANGUAGE_PT, expected)
    rendered_pt = _slide_numbers(output_dir / LANGUAGE_PT)
    rendered_en = _slide_numbers(output_dir / LANGUAGE_EN)
    if _requires_english(request):
        errors.extend(_validate_language(output_dir, LANGUAGE_EN, expected))
    raw_root = serving_paths.project_root if serving_paths is not None else output_dir
    errors.extend(_validate_raw_images(request, raw_root))
    errors.extend(_validate_pdfs(request, output_dir, expected))
    # Pre-promotion outputs have no versioned manifest yet (it is written during
    # the artifact build); the still-active version's manifest is irrelevant to
    # the fresh render, so the manifest check is skipped in that mode.
    if request.project.artifact_version and not request.validate_pre_promotion:
        errors.extend(_validate_manifest(request.project))
    return _report(
        ReportInput(
            errors=tuple(errors),
            warnings=warnings,
            rendered_pt=rendered_pt,
            rendered_en=rendered_en,
        )
    )


def format_artifact_health_errors(errors: Sequence[str]) -> str:
    """Compact health errors for DB fields and HTTP responses."""
    if not errors:
        return "carousel artifacts are incomplete"
    return "; ".join(errors)


def _report(report_input: ReportInput) -> CarouselArtifactHealthReport:
    return CarouselArtifactHealthReport(
        ok=not report_input.errors,
        errors=report_input.errors,
        warnings=tuple(report_input.warnings),
        rendered_slide_numbers_pt=report_input.rendered_pt,
        rendered_slide_numbers_en=report_input.rendered_en,
    )


def _health_root(
    serving_paths: ArtifactServingPaths | None,
    *,
    validate_pre_promotion: bool,
) -> Path | None:
    """Pick the root to validate: project root pre-promotion, else serving root."""
    if serving_paths is None:
        return None
    if validate_pre_promotion:
        return serving_paths.project_root
    return serving_paths.serving_root


def _resolved_output_dir(project: CarouselProject) -> Path | None:
    serving_paths = resolve_and_reconcile_serving_paths(project)
    if serving_paths is None:
        return None
    return serving_paths.serving_root


def _validate_manifest(project: CarouselProject) -> list[str]:
    manifest_path = resolve_manifest_path(project)
    if manifest_path is None or not manifest_path.is_file():
        return [ERR_ARTIFACT_MANIFEST_MISSING]
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return [ERR_ARTIFACT_MANIFEST_INVALID]
    if not isinstance(payload, dict):
        return [ERR_ARTIFACT_MANIFEST_INVALID]
    try:
        typed_payload = CarouselArtifactManifestPayload.model_validate(payload)
        manifest = manifest_from_payload(typed_payload)
    except (KeyError, TypeError, ValueError):
        return [ERR_ARTIFACT_MANIFEST_INVALID]
    errors: list[str] = []
    if manifest.artifact_version != project.artifact_version:
        errors.append(ERR_ARTIFACT_MANIFEST_VERSION_MISMATCH)
    if (
        project.presentation_policy_version
        and manifest.presentation_policy_version != project.presentation_policy_version
    ):
        errors.append(ERR_ARTIFACT_MANIFEST_POLICY_MISMATCH)
    return errors


def _expected_slide_numbers(slides: Sequence[CarouselSlide]) -> tuple[int, ...]:
    return tuple(sorted({slide.slide_number for slide in slides}))


def _requires_english(request: CarouselArtifactHealthRequest) -> bool:
    if request.require_english is not None:
        return request.require_english
    return any(unpack_extras(slide).translation_en for slide in request.slides)


def _validate_language(
    output_dir: Path,
    language: str,
    expected: Sequence[int],
) -> list[str]:
    errors: list[str] = []
    standard_size = ImageDimensions(CAROUSEL_WIDTH, CAROUSEL_HEIGHT)
    hd_size = ImageDimensions(CAROUSEL_WIDTH * 2, CAROUSEL_HEIGHT * 2)
    for slide_number in expected:
        standard = output_dir / language / _slide_filename(slide_number)
        hd = output_dir / language / HD_SUBDIR_NAME / _slide_filename(slide_number)
        errors.extend(_validate_rendered_slide(standard, language, standard_size))
        errors.extend(_validate_hd_slide(hd, language, hd_size))
    return errors


def _validate_rendered_slide(
    path: Path,
    language: str,
    dimensions: ImageDimensions,
) -> list[str]:
    slide_number = _number_from_path(path)
    if not path.is_file():
        return [_MISSING_RENDER.format(language, slide_number)]
    return _validate_jpeg(JpegCheck(path, str(path), dimensions))


def _validate_hd_slide(
    path: Path,
    language: str,
    dimensions: ImageDimensions,
) -> list[str]:
    slide_number = _number_from_path(path)
    if not path.is_file():
        return [_MISSING_HD_RENDER.format(language, slide_number)]
    return _validate_jpeg(JpegCheck(path, str(path), dimensions))


def _validate_raw_images(
    request: CarouselArtifactHealthRequest,
    output_dir: Path,
) -> list[str]:
    if not request.project.generate_images:
        return []
    slide_data = [unpack_extras(slide) for slide in request.slides]
    errors = [
        _MISSING_IMAGE_PROMPT.format(slide.slide_number)
        for slide in slide_data
        if slide.slide_type in IMAGE_SLIDE_TYPES and not slide.image_prompt
    ]
    raw_slide_numbers = [
        slide.slide_number for slide in filter_image_slides(slide_data)
    ]
    for slide_number in raw_slide_numbers:
        path = output_dir / SHARED_IMAGES_DIR_NAME / _slide_filename(slide_number)
        if not path.is_file():
            errors.append(_MISSING_RAW_IMAGE.format(slide_number))
            continue
        errors.extend(_validate_jpeg(JpegCheck(path, str(path), None)))
    return errors


def _validate_pdfs(
    request: CarouselArtifactHealthRequest,
    output_dir: Path,
    expected: Sequence[int],
) -> list[str]:
    checks = [
        _pdf_check(
            PdfCheckRequest(
                project=request.project,
                output_dir=output_dir,
                language=LANGUAGE_PT,
                pages=len(expected),
            )
        )
    ]
    if _requires_english(request):
        checks.append(
            _pdf_check(
                PdfCheckRequest(
                    project=request.project,
                    output_dir=output_dir,
                    language=LANGUAGE_EN,
                    pages=len(expected),
                )
            )
        )
    errors: list[str] = []
    for check in checks:
        errors.extend(_validate_pdf(check))
    return errors


def _pdf_check(request: PdfCheckRequest) -> PdfCheck:
    raw_path = (
        request.project.pdf_path_en
        if request.language == LANGUAGE_EN
        else request.project.pdf_path
    )
    fallback = request.output_dir / request.language / _PDF_FILENAME
    path = _safe_output_file(request.output_dir, raw_path) if raw_path else fallback
    return PdfCheck(path, request.language, request.pages)


def _safe_output_file(output_dir: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path).resolve()
    if not candidate.is_relative_to(output_dir):
        return None
    return candidate


def _validate_pdf(check: PdfCheck) -> list[str]:
    if check.path is None or not check.path.is_file():
        return [_MISSING_PDF.format(check.label)]
    try:
        pages = len(PdfReader(str(check.path)).pages)
    except (OSError, ValueError, PyPdfError) as exc:
        return [_PDF_UNREADABLE.format(check.label, exc)]
    if pages != check.expected_pages:
        return [
            _WRONG_PDF_PAGES.format(check.label, pages, check.expected_pages),
        ]
    return []


def _validate_jpeg(check: JpegCheck) -> list[str]:
    if not check.path.is_file():
        return [_INVALID_JPEG.format(check.label)]
    if check.path.stat().st_size < _MIN_JPEG_BYTES:
        return [_TINY_JPEG.format(check.label)]
    if not is_valid_jpeg(check.path, min_bytes=_MIN_JPEG_BYTES):
        return [_INVALID_JPEG.format(check.label)]
    from PIL import Image as PILImage

    try:
        with PILImage.open(check.path) as image:
            width, height = image.size
    except (OSError, ValueError):
        return [_INVALID_JPEG.format(check.label)]
    return _dimension_errors(check, ImageDimensions(width=width, height=height))


def _dimension_errors(check: JpegCheck, actual: ImageDimensions) -> list[str]:
    expected = check.expected_dimensions
    if expected is None:
        return []
    if actual == expected:
        return []
    return [
        _WRONG_DIMENSIONS.format(
            check.label,
            actual.width,
            actual.height,
            expected.width,
            expected.height,
        )
    ]


def _slide_numbers(slide_dir: Path) -> tuple[int, ...]:
    numbers: set[int] = set()
    if not slide_dir.is_dir():
        return ()
    for path in slide_dir.glob(f"{SLIDE_FILENAME_PREFIX}*{SLIDE_IMAGE_EXTENSION}"):
        number = _number_from_path(path)
        if number > 0:
            numbers.add(number)
    return tuple(sorted(numbers))


def _slide_filename(slide_number: int) -> str:
    return f"{SLIDE_FILENAME_PREFIX}{slide_number}{SLIDE_IMAGE_EXTENSION}"


def _number_from_path(path: Path) -> int:
    stem = path.stem.removeprefix(SLIDE_FILENAME_PREFIX)
    return int(stem) if stem.isdigit() else 0
