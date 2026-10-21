"""Unit tests for Playwright export geometry preflight."""

from __future__ import annotations

import json
import shutil
import subprocess
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.domain.constants.carousel_presentation import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.playwright_geometry import (
    ERR_EXPORT_PREFLIGHT_FAILED,
    VIOLATION_FONT_UNAVAILABLE,
    VIOLATION_IMAGE_DECODE_FAILED,
    VIOLATION_IMAGE_DECODE_TIMEOUT,
    VIOLATION_IMAGE_LOAD_FAILED,
    VIOLATION_LAYOUT_COPY_OVERFLOW,
)
from rag_backend.infrastructure.external.playwright_geometry import (
    GeometryViolation,
    PlaywrightExportPreflightError,
    PreflightReport,
    check_fonts,
    decode_required_images,
    evaluate_geometry,
    run_export_preflight,
)
from rag_backend.infrastructure.external.playwright_geometry_scripts import (
    IMAGE_DECODE_SCRIPT,
)


@pytest.fixture
def policy():
    return load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.evaluate = AsyncMock()
    return page


@pytest.mark.unit
class TestCheckFonts:
    async def test_passes_when_required_fonts_are_available(
        self, mock_page: MagicMock, policy
    ) -> None:
        # Scenario: fonts.ready succeeds and all families are available
        mock_page.evaluate.return_value = [
            {"family": "heading", "available": True, "error_code": None},
            {"family": "body", "available": True, "error_code": None},
            {"family": "badge", "available": True, "error_code": None},
        ]

        violations = await check_fonts(mock_page, policy.fonts)

        assert violations == ()
        mock_page.evaluate.assert_awaited_once()

    async def test_fails_when_required_font_is_unavailable(
        self, mock_page: MagicMock, policy
    ) -> None:
        # Scenario: export preflight rejects fallback fonts
        mock_page.evaluate.return_value = [
            {
                "family": "heading",
                "available": False,
                "error_code": VIOLATION_FONT_UNAVAILABLE,
            },
            {"family": "body", "available": True, "error_code": None},
            {"family": "badge", "available": True, "error_code": None},
        ]

        violations = await check_fonts(mock_page, policy.fonts)

        assert len(violations) == 1
        assert violations[0].code == VIOLATION_FONT_UNAVAILABLE
        assert violations[0].blocking is True


@pytest.mark.unit
class TestDecodeRequiredImages:
    async def test_reports_decode_failures(self, mock_page: MagicMock, policy) -> None:
        # Scenario: corrupt background image cannot decode
        mock_page.evaluate.return_value = [
            {
                "src": "file:///tmp/slide-4.jpg",
                "slide_number": 4,
                "decoded": False,
                "natural_width": 0,
                "natural_height": 0,
                "error_code": VIOLATION_IMAGE_DECODE_FAILED,
            }
        ]

        reports = await decode_required_images(mock_page, policy.geometry.selectors)

        assert len(reports) == 1
        assert reports[0].decoded is False
        assert reports[0].error_code == VIOLATION_IMAGE_DECODE_FAILED


@pytest.mark.unit
class TestDecodeScriptReasons:
    """A rejection is reported for what actually happened.

    The script runs in the browser, so it is executed here with Node and a
    minimal DOM harness (one missing image, one stalled image).
    """

    def test_missing_and_stalled_images_report_precise_reasons(self) -> None:
        node = shutil.which("node")
        assert node is not None, "node is required to run the decode script"
        harness = _DECODE_HARNESS % IMAGE_DECODE_SCRIPT
        result = subprocess.run(
            [node, "-e", harness],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        reports = json.loads(result.stdout.strip().splitlines()[-1])
        by_src = {report["src"]: report for report in reports}
        missing = by_src["file:///images/slide_2.jpg"]
        stalled = by_src["file:///images/slide_1.jpg"]
        assert missing["error_code"] == VIOLATION_IMAGE_LOAD_FAILED
        assert stalled["error_code"] == VIOLATION_IMAGE_DECODE_TIMEOUT

    async def test_the_report_code_flows_into_the_violation(
        self, mock_page: MagicMock, policy
    ) -> None:
        mock_page.evaluate.return_value = [
            {
                "src": "file:///images/slide_2.jpg",
                "slide_number": None,
                "decoded": False,
                "natural_width": 0,
                "natural_height": 0,
                "error_code": VIOLATION_IMAGE_LOAD_FAILED,
            }
        ]
        reports = await decode_required_images(mock_page, policy.geometry.selectors)
        from rag_backend.infrastructure.external.playwright_geometry import (
            _image_violations,
        )

        violations = _image_violations(reports)
        assert len(violations) == 1
        assert violations[0].code == VIOLATION_IMAGE_LOAD_FAILED


_DECODE_HARNESS = r"""
const imgs = {
  missing: {
    tagName: 'IMG',
    currentSrc: 'file:///images/slide_2.jpg',
    src: 'file:///images/slide_2.jpg',
    complete: true,
    naturalWidth: 0,
    naturalHeight: 0,
    decode: () => Promise.reject(new Error('EncodingError')),
    querySelectorAll: () => [],
  },
  stalled: {
    tagName: 'IMG',
    currentSrc: 'file:///images/slide_1.jpg',
    src: 'file:///images/slide_1.jpg',
    complete: false,
    naturalWidth: 300,
    naturalHeight: 300,
    decode: () => new Promise((_, reject) => {
      setTimeout(() => reject(new Error('late')), 2000);
    }),
    querySelectorAll: () => [],
  },
};
globalThis.document = {
  querySelectorAll: (selector) => {
    if (selector === 'artwork') return [imgs.missing];
    if (selector === 'avatar') return [imgs.stalled];
    return [];
  },
};
const decodeFn = (%s);
decodeFn({
  artworkSelector: 'artwork',
  avatarSelector: 'avatar',
  timeoutPer: 50,
  timeoutTotal: 5000,
}).then((reports) => {
  console.log(JSON.stringify(reports));
  process.exit(0);
}, (error) => {
  console.error(String(error));
  process.exit(1);
});
"""


@pytest.mark.unit
class TestEvaluateGeometry:
    async def test_detects_copy_overflow(self, mock_page: MagicMock, policy) -> None:
        # Scenario: lower-third copy exceeds client height
        mock_page.evaluate.return_value = {
            "skipped": False,
            "violations": [
                {
                    "code": VIOLATION_LAYOUT_COPY_OVERFLOW,
                    "slide_number": 3,
                    "message": "Copy content exceeds client height",
                    "blocking": True,
                }
            ],
            "warnings": [],
            "slideReports": [
                {
                    "slide_number": 3,
                    "slide_type": "content",
                    "passed": False,
                    "violations": [
                        {
                            "code": VIOLATION_LAYOUT_COPY_OVERFLOW,
                            "slide_number": 3,
                            "message": "Copy content exceeds client height",
                            "blocking": True,
                        }
                    ],
                    "warnings": [],
                }
            ],
        }

        skipped, slide_reports, violations, warnings = await evaluate_geometry(
            mock_page,
            policy,
            hd=False,
        )

        assert skipped is False
        assert len(slide_reports) == 1
        assert slide_reports[0].passed is False
        assert violations[0].code == VIOLATION_LAYOUT_COPY_OVERFLOW
        assert warnings == ()

    async def test_skips_when_contract_slides_are_absent(
        self, mock_page: MagicMock, policy
    ) -> None:
        mock_page.evaluate.return_value = {
            "skipped": True,
            "violations": [],
            "warnings": [],
            "slideReports": [],
        }

        skipped, slide_reports, violations, warnings = await evaluate_geometry(
            mock_page,
            policy,
            hd=False,
        )

        assert skipped is True
        assert slide_reports == ()
        assert violations == ()
        assert warnings == ()


@pytest.mark.unit
class TestRunExportPreflight:
    async def test_raises_on_blocking_violations(
        self, mock_page: MagicMock, policy
    ) -> None:
        mock_page.evaluate.side_effect = [
            [{"family": "heading", "available": True, "error_code": None}],
            [],
            {
                "skipped": False,
                "violations": [
                    {
                        "code": VIOLATION_LAYOUT_COPY_OVERFLOW,
                        "slide_number": 2,
                        "message": "Copy content exceeds client height",
                        "blocking": True,
                    }
                ],
                "warnings": [],
                "slideReports": [],
            },
        ]

        with pytest.raises(PlaywrightExportPreflightError) as exc_info:
            await run_export_preflight(mock_page, policy, hd=False)

        assert str(exc_info.value) == ERR_EXPORT_PREFLIGHT_FAILED
        assert exc_info.value.report is not None
        assert exc_info.value.report.blocking_violations[0].slide_number == 2

    async def test_returns_report_when_preflight_passes(
        self, mock_page: MagicMock, policy
    ) -> None:
        mock_page.evaluate.side_effect = [
            [
                {"family": "heading", "available": True, "error_code": None},
                {"family": "body", "available": True, "error_code": None},
                {"family": "badge", "available": True, "error_code": None},
            ],
            [
                {
                    "src": "file:///tmp/artwork.jpg",
                    "slide_number": None,
                    "decoded": True,
                    "natural_width": 1080,
                    "natural_height": 1350,
                    "error_code": None,
                }
            ],
            {
                "skipped": True,
                "violations": [],
                "warnings": [],
                "slideReports": [],
            },
        ]

        report = await run_export_preflight(mock_page, policy, hd=False)

        assert isinstance(report, PreflightReport)
        assert report.passed is True
        assert report.geometry_skipped is True
        assert report.blocking_violations == ()


@pytest.mark.unit
class TestPreflightReport:
    def test_blocking_violations_filters_non_blocking(self) -> None:
        report = PreflightReport(
            passed=False,
            scale="standard",
            geometry_skipped=False,
            slide_reports=(),
            image_reports=(),
            violations=(
                GeometryViolation(
                    code=VIOLATION_LAYOUT_COPY_OVERFLOW,
                    slide_number=1,
                    message="overflow",
                    blocking=True,
                ),
                GeometryViolation(
                    code="layout_near_limit",
                    slide_number=1,
                    message="near limit",
                    blocking=False,
                ),
            ),
            warnings=(),
        )

        assert len(report.blocking_violations) == 1
        assert report.blocking_violations[0].code == VIOLATION_LAYOUT_COPY_OVERFLOW
