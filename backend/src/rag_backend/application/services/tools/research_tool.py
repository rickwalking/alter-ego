"""Web research tool for carousel content generation."""

from rag_backend.application.services.tools.research_fetch import (
    fetch_public_document,
    strip_resource_hints,
)
from rag_backend.application.services.tools.research_route_guard import (
    block_all_requests,
)
from rag_backend.domain.constants.url_safety import (
    CHROMIUM_DISABLE_DNS_PREFETCH,
    MEDIA_TYPE_TEXT_PLAIN,
    RESEARCH_TEXT_MAX_CHARS,
    ROUTE_ALL_REQUESTS,
)
from rag_backend.domain.models import ResearchSourceType
from rag_backend.domain.protocols import ResearchTool


class PlaywrightResearchTool(ResearchTool):
    """Playwright-based web research implementation."""

    @staticmethod
    async def scrape_url(url: str) -> str:
        """Scrape and extract content from a URL.

        The document is fetched with redirects off and every hop checked
        before it is requested (QA r2 R2). Chromium only renders that HTML,
        with JavaScript off and every page request aborted, so it never
        reaches the network. Raises ``UnsafeResearchTargetError`` when the URL
        or any redirect hop is not allowed.

        Plain text is returned as is. Before rendering, resource hints are
        stripped and DNS prefetch is off, so the HTML cannot make Chromium
        resolve or connect to a host (QA r3 Q6).
        """
        from playwright.async_api import async_playwright

        document = await fetch_public_document(url)
        if document.media_type == MEDIA_TYPE_TEXT_PLAIN:
            return document.html[:RESEARCH_TEXT_MAX_CHARS]
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, args=[CHROMIUM_DISABLE_DNS_PREFETCH]
            )
            page = await browser.new_page(java_script_enabled=False)
            try:
                await page.route(ROUTE_ALL_REQUESTS, block_all_requests)
                await page.set_content(
                    strip_resource_hints(document.html),
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
                content = await page.inner_text("body")
                return content[:RESEARCH_TEXT_MAX_CHARS]
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
