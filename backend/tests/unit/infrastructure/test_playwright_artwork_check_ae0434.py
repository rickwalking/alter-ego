"""Export preflight names missing slide artwork (AE-0434).

Gherkin: tests/features/carousel_export_artwork_ae0434.feature
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rag_backend.domain.constants.playwright_geometry import (
    PREFLIGHT_SCALE_HD,
    VIOLATION_SLIDE_ARTWORK_MISSING,
)
from rag_backend.infrastructure.external.playwright_artwork_check import (
    ensure_artwork_files,
    missing_artwork_violations,
)
from rag_backend.infrastructure.external.playwright_export import (
    PlaywrightExportService,
)
from rag_backend.infrastructure.external.playwright_geometry import (
    PlaywrightExportPreflightError,
)


def _slide(src: str | None) -> str:
    artwork = (
        f'<div class="slide-artwork">\n    <img src="{src}" alt="" />\n  </div>'
        if src is not None
        else '<div class="slide-artwork slide-artwork-none" aria-hidden="true"></div>'
    )
    return f'<div class="ig-slide"><div class="ig-slide-inner">{artwork}</div></div>'


def _html(*srcs: str | None) -> str:
    return "<html><body>" + "".join(_slide(s) for s in srcs) + "</body></html>"


def _images(root: Path, *numbers: int) -> None:
    (root / "images").mkdir(parents=True, exist_ok=True)
    for number in numbers:
        (root / "images" / f"slide_{number}.jpg").write_bytes(b"jpg")


_DECK = _html(
    "../images/slide_1.jpg",
    "../images/slide_2.jpg",
    "../images/slide_3.jpg",
    "../images/slide_4.jpg",
    "../images/slide_5.jpg",
    "../images/slide_6.jpg",
    None,
)


@pytest.mark.unit
class TestMissingArtwork:
    # Scenario: A missing artwork file fails the preflight with a clear reason
    def test_names_missing_slides(self, tmp_path: Path) -> None:
        _images(tmp_path, 1, 3, 4, 5)
        lang_dir = tmp_path / "pt"
        lang_dir.mkdir()
        with pytest.raises(PlaywrightExportPreflightError) as caught:
            ensure_artwork_files(_DECK, lang_dir)
        assert str(caught.value) == (
            "export_preflight_failed: slide_artwork_missing: slide_2, slide_6"
        )
        report = caught.value.report
        assert report is not None
        assert report.passed is False
        assert [
            (v.code, v.slide_number, v.blocking) for v in report.blocking_violations
        ] == [
            (VIOLATION_SLIDE_ARTWORK_MISSING, 2, True),
            (VIOLATION_SLIDE_ARTWORK_MISSING, 6, True),
        ]
        assert report.violations[0].message == (
            "slide_artwork_missing: slide_2 (../images/slide_2.jpg)"
        )

    def test_hd_scale_on_report(self, tmp_path: Path) -> None:
        with pytest.raises(PlaywrightExportPreflightError) as caught:
            ensure_artwork_files(_html("images/slide_1.jpg"), tmp_path, hd=True)
        assert caught.value.report is not None
        assert caught.value.report.scale == PREFLIGHT_SCALE_HD

    # Scenario: Summary and closing slides without images export
    def test_all_present_passes(self, tmp_path: Path) -> None:
        _images(tmp_path, 1, 2, 3, 4, 5, 6)
        lang_dir = tmp_path / "pt"
        lang_dir.mkdir()
        ensure_artwork_files(_DECK, lang_dir)
        assert missing_artwork_violations(_DECK, lang_dir) == ()

    # Scenario: Remote artwork is not checked on disk
    def test_remote_and_absent_artwork_ignored(self, tmp_path: Path) -> None:
        html = _html("https://cdn.example/x.jpg", "data:image/png;base64,AA", None)
        assert missing_artwork_violations(html, tmp_path) == ()

    def test_url_encoded_src_resolves(self, tmp_path: Path) -> None:
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "my cover.jpg").write_bytes(b"jpg")
        html = _html("assets/my%20cover.jpg")
        assert missing_artwork_violations(html, tmp_path) == ()


@pytest.mark.unit
class TestExportRunsCheckFirst:
    # Scenario: The missing-artwork check runs before Playwright
    async def test_fails_before_browser_launch(self, tmp_path: Path) -> None:
        launcher = MagicMock()
        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                launcher,
            ),
            pytest.raises(
                PlaywrightExportPreflightError, match="slide_artwork_missing: slide_2"
            ),
        ):
            await PlaywrightExportService.export_slides(
                html_content=_html(None, "images/slide_2.jpg"),
                output_dir=str(tmp_path),
            )
        launcher.assert_not_called()
