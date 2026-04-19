"""Web research tool for carousel content generation."""

from rag_backend.domain.models import ResearchSourceType
from rag_backend.domain.protocols import ResearchTool


class PlaywrightResearchTool(ResearchTool):
    """Playwright-based web research implementation."""

    async def scrape_url(self, url: str) -> str:
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

    async def search_web(
        self, query: str, source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]:
        """Search the web for relevant sources.

        Returns list of dicts with 'url', 'title', 'snippet' keys.
        """
        from playwright.async_api import async_playwright

        search_url = f"https://www.google.com/search?q={query}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                results = await page.evaluate("""() => {
                    const items = document.querySelectorAll('.g');
                    return Array.from(items).slice(0, 10).map(item => {
                        const link = item.querySelector('a');
                        const titleEl = item.querySelector('h3');
                        const snippetEl = item.querySelector('.VwiC3b');
                        return {
                            url: link ? link.href : '',
                            title: titleEl ? titleEl.textContent : '',
                            snippet: snippetEl ? snippetEl.textContent : ''
                        };
                    });
                }""")
                return results
            finally:
                await browser.close()
