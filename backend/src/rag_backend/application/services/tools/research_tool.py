"""Web research tool for carousel content generation."""

from rag_backend.domain.models import ResearchSourceType
from rag_backend.domain.protocols import ResearchTool


class PlaywrightResearchTool(ResearchTool):
    """Playwright-based web research implementation."""

    @staticmethod
    async def scrape_url(url: str) -> str:
        """Scrape and extract content from a URL."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                content = await page.inner_text("body")
                return content[:10000]  # Limit content length
            finally:
                await browser.close()

    @staticmethod
    async def search_web(
        query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]:
        """Search the web via the `ddgs` library (DuckDuckGo + fallbacks).

        DuckDuckGo's HTML endpoint returns 403 to headless browsers from many
        server IPs, so we use the `ddgs` client library which handles UA
        rotation, backend fallbacks, and returns clean results.

        Runs the sync `DDGS.text()` call in a worker thread so it doesn't
        block the event loop.

        Returns list of dicts with 'url', 'title', 'snippet' keys.
        """
        import asyncio

        from ddgs import DDGS

        def _search_sync() -> list[dict[str, str]]:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=10))
            return [
                {
                    "url": r.get("href", ""),
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw
                if r.get("href")
            ]

        return await asyncio.to_thread(_search_sync)
