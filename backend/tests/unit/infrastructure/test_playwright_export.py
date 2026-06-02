"""Unit tests for Playwright export service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.domain.protocols import ExportConfig
from rag_backend.infrastructure.external.playwright_export import (
    PlaywrightExportService,
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
        mock_playwright, mock_browser, _, _ = self._make_mock_browser_page()

        with patch(
            "rag_backend.infrastructure.external.playwright_export.async_playwright",
            return_value=mock_playwright,
        ):
            result = await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
            )

        assert len(result) == 1
        mock_browser.close.assert_awaited_once()

    async def test_exports_with_css_overrides(self, tmp_path: Path) -> None:
        service = PlaywrightExportService()
        mock_playwright, _, mock_page, _ = self._make_mock_browser_page()

        with patch(
            "rag_backend.infrastructure.external.playwright_export.async_playwright",
            return_value=mock_playwright,
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
        mock_playwright, mock_browser, _, _ = self._make_mock_browser_page()

        with patch(
            "rag_backend.infrastructure.external.playwright_export.async_playwright",
            return_value=mock_playwright,
        ):
            result = await service.export_slides(
                html_content="<html><div class='ig-slide-inner'></div></html>",
                output_dir=str(tmp_path),
                config=ExportConfig(hd=True),
            )

        assert len(result) == 1
        new_page_call = mock_browser.new_page.await_args
        assert new_page_call.kwargs["device_scale_factor"] == 2

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

        with patch(
            "rag_backend.infrastructure.external.playwright_export.async_playwright",
            return_value=mock_playwright,
        ):
            result = await service.export_slides(
                html_content="<html><div class='slide'></div></html>",
                output_dir=str(tmp_path),
            )

        assert len(result) == 1
