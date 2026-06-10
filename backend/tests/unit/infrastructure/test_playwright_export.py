"""Unit tests for Playwright export service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.domain.protocols import ExportConfig
from rag_backend.infrastructure.external.playwright_export import (
    PlaywrightExportService,
    _crop_border_artifact,
)
from rag_backend.infrastructure.external.playwright_geometry import (
    PlaywrightExportPreflightError,
)


class MockLocator:
    def __init__(self, elements):
        self._elements = elements
        self.all = AsyncMock(return_value=elements)


class MockPage:
    def __init__(self, elements):
        self._elements = elements
        self.goto = AsyncMock()
        self.wait_for_timeout = AsyncMock()
        self.evaluate = AsyncMock()

    def locator(self, _selector: str):
        return MockLocator(self._elements)


class MockBrowser:
    def __init__(self, page):
        self._page = page
        self.new_page = AsyncMock(return_value=page)
        self.close = AsyncMock()


class MockChromium:
    def __init__(self, browser):
        self._browser = browser
        self.launch = AsyncMock(return_value=browser)


class MockPlaywright:
    def __init__(self, browser):
        self.chromium = MockChromium(browser)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.unit
class TestPlaywrightExportService:
    def _make_mock_browser_page(self, elements=None):
        """Build a page mock where locator() is sync and .all() is async."""
        mock_element = MagicMock()
        mock_element.screenshot = AsyncMock()
        elements = elements or [mock_element]
        mock_page = MockPage(elements)
        mock_browser = MockBrowser(mock_page)
        mock_playwright = MockPlaywright(mock_browser)
        return mock_playwright, mock_browser, mock_page, mock_element

    async def test_exports_slides(self, tmp_path: Path) -> None:
        service = PlaywrightExportService()
        mock_playwright, mock_browser, _, mock_element = self._make_mock_browser_page()

        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                return_value=mock_playwright,
            ),
            patch(
                "rag_backend.infrastructure.external.playwright_export.run_export_preflight",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
            )

        assert len(result) == 1
        mock_browser.close.assert_awaited_once()
        screenshot_call = mock_element.screenshot.await_args
        assert screenshot_call.kwargs.get("scale") == "css"

    async def test_exports_with_css_overrides(self, tmp_path: Path) -> None:
        service = PlaywrightExportService()
        mock_playwright, _, mock_page, _ = self._make_mock_browser_page()

        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                return_value=mock_playwright,
            ),
            patch(
                "rag_backend.infrastructure.external.playwright_export.run_export_preflight",
                new_callable=AsyncMock,
            ),
        ):
            await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
                config=ExportConfig(css_overrides="body { margin: 0; }"),
            )

        evaluate_calls = mock_page.evaluate.await_args_list
        assert len(evaluate_calls) == 2  # default injection + override

    async def test_exports_hd(self, tmp_path: Path) -> None:
        service = PlaywrightExportService()
        mock_playwright, mock_browser, _, mock_element = self._make_mock_browser_page()

        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                return_value=mock_playwright,
            ),
            patch(
                "rag_backend.infrastructure.external.playwright_export.run_export_preflight",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
                config=ExportConfig(hd=True),
            )

        assert len(result) == 1
        new_page_call = mock_browser.new_page.await_args
        assert new_page_call.kwargs["device_scale_factor"] == 2
        screenshot_call = mock_element.screenshot.await_args
        assert screenshot_call.kwargs.get("scale") == "css"

    async def test_export_overrides_scale_readability_chrome(
        self, tmp_path: Path
    ) -> None:
        service = PlaywrightExportService()
        mock_playwright, _, mock_page, _ = self._make_mock_browser_page()

        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                return_value=mock_playwright,
            ),
            patch(
                "rag_backend.infrastructure.external.playwright_export.run_export_preflight",
                new_callable=AsyncMock,
            ),
        ):
            await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
            )

        injection = mock_page.evaluate.await_args_list[0].args[0]
        assert ".s1-swipe       { font-size: 26px !important; }" in injection
        assert ".counter-label  { font-size: 22px !important; }" in injection
        assert ".slide-hero-content { padding: 44px 40px 160px !important; }" in injection
        assert ".slide-presentation { padding: 44px 40px 160px !important; }" in injection
        assert (
            ".slide-hero-main,\n"
            "  .slide-presentation-copy { max-height: calc(100% - 190px) !important; }"
        ) in injection
        assert ".creator-watermark-avatar { width: 72px !important;" in injection
        assert ".closing-avatar { width: 168px !important;" in injection

    async def test_fallback_to_legacy_slide_selector(self, tmp_path: Path) -> None:
        service = PlaywrightExportService()
        mock_element = MagicMock()
        mock_element.screenshot = AsyncMock()
        # First call returns empty, second call returns element
        mock_locator1 = MockLocator([])
        mock_locator2 = MockLocator([mock_element])
        call_count = 0

        class FallbackMockPage:
            def __init__(self):
                self.goto = AsyncMock()
                self.wait_for_timeout = AsyncMock()
                self.evaluate = AsyncMock()

            def locator(self, _selector: str):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_locator1
                return mock_locator2

        mock_page = FallbackMockPage()
        mock_browser = MockBrowser(mock_page)
        mock_playwright = MockPlaywright(mock_browser)

        with (
            patch(
                "rag_backend.infrastructure.external.playwright_export.async_playwright",
                return_value=mock_playwright,
            ),
            patch(
                "rag_backend.infrastructure.external.playwright_export.run_export_preflight",
                new_callable=AsyncMock,
            ),
        ):
            result = await service.export_slides(
                html_content="<html><div class='slide'></div></html>",
                output_dir=str(tmp_path),
            )

        assert len(result) == 1


@pytest.mark.unit
class TestCropBorderArtifact:
    def test_crops_odd_pixel_excess_to_exact_target(self, tmp_path: Path) -> None:
        from PIL import Image as PILImage

        image_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (1081, 1351), color="white").save(image_path, "JPEG")

        _crop_border_artifact(str(image_path), 1080, 1350)

        with PILImage.open(image_path) as cropped:
            assert cropped.size == (1080, 1350)

    def test_raises_when_dimension_mismatch_exceeds_tolerance(
        self, tmp_path: Path
    ) -> None:
        from PIL import Image as PILImage

        image_path = tmp_path / "slide_1.jpg"
        PILImage.new("RGB", (1090, 1350), color="white").save(image_path, "JPEG")

        with pytest.raises(PlaywrightExportPreflightError):
            _crop_border_artifact(str(image_path), 1080, 1350)
