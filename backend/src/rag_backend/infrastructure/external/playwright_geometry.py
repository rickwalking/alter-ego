"""Playwright export preflight: fonts, image decode, and layout geometry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from playwright.async_api import Page

from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
    FontPolicy,
)
from rag_backend.domain.constants.playwright_geometry import (
    ERR_EXPORT_PREFLIGHT_FAILED,
    FONT_CHECK_BADGE_SIZE_PX,
    FONT_CHECK_BODY_SIZE_PX,
    FONT_CHECK_HEADING_SIZE_PX,
    FONT_READY_TIMEOUT_MS,
    IMAGE_DECODE_TIMEOUT_PER_MS,
    IMAGE_DECODE_TIMEOUT_TOTAL_MS,
    PREFLIGHT_SCALE_HD,
    PREFLIGHT_SCALE_STANDARD,
    VIOLATION_FONT_READY_TIMEOUT,
    VIOLATION_FONT_UNAVAILABLE,
    VIOLATION_IMAGE_DECODE_FAILED,
)
from rag_backend.infrastructure.external.playwright_geometry_scripts import (
    FONT_CHECK_SCRIPT,
    GEOMETRY_EVAL_SCRIPT,
    IMAGE_DECODE_SCRIPT,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


@dataclass(frozen=True)
class GeometryViolation:
    """Single layout or asset violation from export preflight."""

    code: str
    slide_number: int | None
    message: str
    blocking: bool


@dataclass(frozen=True)
class SlideGeometryReport:
    """Geometry evaluation result for one slide."""

    slide_number: int
    slide_type: str
    passed: bool
    violations: tuple[GeometryViolation, ...]
    warnings: tuple[GeometryViolation, ...]


@dataclass(frozen=True)
class ImageDecodeReport:
    """Image decode result for one required image."""

    src: str
    slide_number: int | None
    decoded: bool
    natural_width: int
    natural_height: int
    error_code: str | None


@dataclass(frozen=True)
class PreflightReport:
    """Combined export preflight report."""

    passed: bool
    scale: str
    geometry_skipped: bool
    slide_reports: tuple[SlideGeometryReport, ...]
    image_reports: tuple[ImageDecodeReport, ...]
    violations: tuple[GeometryViolation, ...]
    warnings: tuple[GeometryViolation, ...]

    @property
    def blocking_violations(self) -> tuple[GeometryViolation, ...]:
        return tuple(item for item in self.violations if item.blocking)


class PlaywrightExportPreflightError(RuntimeError):
    """Raised when export preflight finds blocking violations."""

    def __init__(self, message: str, report: PreflightReport | None = None) -> None:
        super().__init__(message)
        self.report = report


def _font_specs(fonts: FontPolicy) -> list[dict[str, str]]:
    return [
        {
            "label": "heading",
            "cssText": f"{FONT_CHECK_HEADING_SIZE_PX}px {fonts.heading_family}",
        },
        {
            "label": "body",
            "cssText": f"{FONT_CHECK_BODY_SIZE_PX}px {fonts.body_family}",
        },
        {
            "label": "badge",
            "cssText": f"{FONT_CHECK_BADGE_SIZE_PX}px {fonts.badge_family}",
        },
    ]


def _parse_violations(raw_items: list[dict[str, object]]) -> tuple[GeometryViolation, ...]:
    parsed: list[GeometryViolation] = []
    for item in raw_items:
        slide_raw = item.get("slide_number")
        slide_number = int(slide_raw) if isinstance(slide_raw, int) else None
        parsed.append(
            GeometryViolation(
                code=str(item.get("code", "")),
                slide_number=slide_number,
                message=str(item.get("message", "")),
                blocking=bool(item.get("blocking", True)),
            )
        )
    return tuple(parsed)


def _parse_slide_reports(
    raw_items: list[dict[str, object]],
) -> tuple[SlideGeometryReport, ...]:
    reports: list[SlideGeometryReport] = []
    for item in raw_items:
        violations = _parse_violations(cast(list[dict[str, object]], item.get("violations", [])))
        warnings = _parse_violations(cast(list[dict[str, object]], item.get("warnings", [])))
        reports.append(
            SlideGeometryReport(
                slide_number=int(item["slide_number"]),
                slide_type=str(item.get("slide_type", "")),
                passed=bool(item.get("passed", False)),
                violations=violations,
                warnings=warnings,
            )
        )
    return tuple(reports)


def _parse_image_reports(raw_items: list[dict[str, object]]) -> tuple[ImageDecodeReport, ...]:
    reports: list[ImageDecodeReport] = []
    for item in raw_items:
        slide_raw = item.get("slide_number")
        slide_number = int(slide_raw) if isinstance(slide_raw, int) else None
        error_raw = item.get("error_code")
        reports.append(
            ImageDecodeReport(
                src=str(item.get("src", "")),
                slide_number=slide_number,
                decoded=bool(item.get("decoded", False)),
                natural_width=int(item.get("natural_width", 0)),
                natural_height=int(item.get("natural_height", 0)),
                error_code=str(error_raw) if error_raw else None,
            )
        )
    return tuple(reports)


def _geometry_params(policy: CarouselPresentationPolicy, *, hd: bool) -> dict[str, object]:
    geometry = policy.geometry
    footer_gap = geometry.footer_gap_hd if hd else geometry.footer_gap_standard
    tolerance = geometry.tolerance_hd if hd else geometry.tolerance_standard
    near_limit = geometry.near_limit_hd if hd else geometry.near_limit_standard
    slides_meta = [
        {
            "slideNumber": slide.slide_number,
            "slideType": slide.slide_type,
            "copyStartRatio": slide.copy_start_ratio,
            "isCta": slide.slide_type == "cta",
            "website": None,
        }
        for slide in policy.slides
    ]
    return {
        "selectors": geometry.selectors,
        "footerGap": footer_gap,
        "tolerance": tolerance,
        "nearLimit": near_limit,
        "slidesMeta": slides_meta,
    }


async def check_fonts(page: Page, fonts: FontPolicy) -> tuple[GeometryViolation, ...]:
    """Wait for document.fonts.ready and verify required families."""
    try:
        raw_checks = await page.evaluate(
            FONT_CHECK_SCRIPT,
            {
                "fontSpecs": _font_specs(fonts),
                "timeoutMs": FONT_READY_TIMEOUT_MS,
            },
        )
    except Exception as exc:
        logger.warning("export_preflight_font_ready_failed", error=str(exc))
        return (
            GeometryViolation(
                code=VIOLATION_FONT_READY_TIMEOUT,
                slide_number=None,
                message="Timed out waiting for document.fonts.ready",
                blocking=True,
            ),
        )

    violations: list[GeometryViolation] = []
    for item in cast(list[dict[str, object]], raw_checks):
        if bool(item.get("available", False)):
            continue
        code = str(item.get("error_code", VIOLATION_FONT_UNAVAILABLE))
        label = str(item.get("family", "unknown"))
        violations.append(
            GeometryViolation(
                code=code,
                slide_number=None,
                message=f"Required font unavailable: {label}",
                blocking=True,
            )
        )
    return tuple(violations)


async def decode_required_images(
    page: Page,
    selectors: dict[str, str],
) -> tuple[ImageDecodeReport, ...]:
    """Decode artwork and avatar images before screenshot capture."""
    raw_reports = await page.evaluate(
        IMAGE_DECODE_SCRIPT,
        {
            "artworkSelector": selectors.get("artwork", ""),
            "avatarSelector": selectors.get("cta_avatar", ""),
            "timeoutPer": IMAGE_DECODE_TIMEOUT_PER_MS,
            "timeoutTotal": IMAGE_DECODE_TIMEOUT_TOTAL_MS,
        },
    )
    return _parse_image_reports(cast(list[dict[str, object]], raw_reports))


async def evaluate_geometry(
    page: Page,
    policy: CarouselPresentationPolicy,
    *,
    hd: bool,
) -> tuple[bool, tuple[SlideGeometryReport, ...], tuple[GeometryViolation, ...], tuple[GeometryViolation, ...]]:
    """Evaluate lower-third geometry predicates for contract-marked slides."""
    raw = await page.evaluate(GEOMETRY_EVAL_SCRIPT, _geometry_params(policy, hd=hd))
    skipped = bool(raw.get("skipped", False))
    slide_reports = _parse_slide_reports(
        cast(list[dict[str, object]], raw.get("slideReports", []))
    )
    violations = _parse_violations(cast(list[dict[str, object]], raw.get("violations", [])))
    warnings = _parse_violations(cast(list[dict[str, object]], raw.get("warnings", [])))
    return skipped, slide_reports, violations, warnings


def _image_violations(reports: tuple[ImageDecodeReport, ...]) -> tuple[GeometryViolation, ...]:
    violations: list[GeometryViolation] = []
    for report in reports:
        if report.decoded:
            continue
        code = report.error_code or VIOLATION_IMAGE_DECODE_FAILED
        violations.append(
            GeometryViolation(
                code=code,
                slide_number=report.slide_number,
                message=f"Required image failed to decode: {report.src}",
                blocking=True,
            )
        )
    return tuple(violations)


async def run_export_preflight(
    page: Page,
    policy: CarouselPresentationPolicy,
    *,
    hd: bool = False,
) -> PreflightReport:
    """Run font, image decode, and geometry checks before screenshot export."""
    scale = PREFLIGHT_SCALE_HD if hd else PREFLIGHT_SCALE_STANDARD
    font_violations = await check_fonts(page, policy.fonts)
    image_reports = await decode_required_images(page, policy.geometry.selectors)
    image_violations = _image_violations(image_reports)

    geometry_skipped, slide_reports, geometry_violations, warnings = await evaluate_geometry(
        page,
        policy,
        hd=hd,
    )

    all_violations = (*font_violations, *image_violations, *geometry_violations)
    blocking = tuple(item for item in all_violations if item.blocking)
    passed = len(blocking) == 0

    report = PreflightReport(
        passed=passed,
        scale=scale,
        geometry_skipped=geometry_skipped,
        slide_reports=slide_reports,
        image_reports=image_reports,
        violations=all_violations,
        warnings=warnings,
    )

    if blocking:
        logger.warning(
            "export_preflight_failed",
            scale=scale,
            violation_codes=[item.code for item in blocking],
            geometry_skipped=geometry_skipped,
        )
        raise PlaywrightExportPreflightError(
            ERR_EXPORT_PREFLIGHT_FAILED,
            report=report,
        )

    logger.info(
        "export_preflight_passed",
        scale=scale,
        geometry_skipped=geometry_skipped,
        warning_codes=[item.code for item in warnings],
    )
    return report


def format_preflight_report(report: PreflightReport) -> str:
    """Serialize a preflight report for logs or error detail."""
    payload = {
        "passed": report.passed,
        "scale": report.scale,
        "geometry_skipped": report.geometry_skipped,
        "blocking_violations": [
            {
                "code": item.code,
                "slide_number": item.slide_number,
                "message": item.message,
            }
            for item in report.blocking_violations
        ],
    }
    return json.dumps(payload, sort_keys=True)
