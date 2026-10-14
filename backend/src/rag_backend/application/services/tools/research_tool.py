"""Web research tool for carousel content generation."""

from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
)
from rag_backend.domain.constants.url_safety import (
    ERR_UNSAFE_REDIRECT,
    PAGE_EVENT_REQUEST,
    ROUTE_ALL_REQUESTS,
)
from rag_backend.domain.models import ResearchSourceType
from rag_backend.domain.protocols import ResearchTool


class PlaywrightResearchTool(ResearchTool):
    """Playwright-based web research implementation."""

    @staticmethod
    async def scrape_url(url: str) -> str:
        """Scrape and extract content from a URL.

        Every request the page makes (redirect hops and sub-resources) passes
        the SSRF guard first (QA r1 S-W1). Raises ``UnsafeResearchTargetError``
        when the URL or any hop is not allowed.
        """
        from playwright.async_api import async_playwright

        guard = ScrapeRouteGuard()
        if not await guard.allows(url):
            raise UnsafeResearchTargetError(ERR_UNSAFE_REDIRECT)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.route(ROUTE_ALL_REQUESTS, guard.handle)
                page.on(PAGE_EVENT_REQUEST, guard.record)
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await guard.verify(page.url)
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
