"""The research scraper never lets Chromium make a network request (QA r1 S-W1, r2 R2).

Playwright does not route redirect hops through ``page.route``, so the
browser no longer navigates at all: the document is fetched hop by hop by
``GuardedDocumentFetcher`` (see ``test_research_fetch_redirects.py``), then
rendered with ``page.set_content`` while every page request is aborted.

Feature: tests/features/url_safety_ssrf.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import pytest

from rag_backend.application.services.tools import research_tool
from rag_backend.application.services.tools.research_fetch import FetchedDocument
from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
    block_all_requests,
)
from rag_backend.domain import url_safety

_PUBLIC_URL = "https://news.example.com/story"
_REBOUND_URL = "https://rebind.example.net/x"
_HTML = (
    "<html><body><p>article text</p><img src='http://169.254.169.254/x'></body></html>"
)


async def _resolve(host: str) -> tuple[str, ...]:
    if host == "rebind.example.net":
        return ("10.0.0.7",)
    return ("93.184.216.34",)


@dataclass(frozen=True)
class _Request:
    url: str
    resource_type: str = "document"


@dataclass
class _Route:
    request: _Request
    outcome: list[str] = field(default_factory=list)

    async def abort(self, error_code: str | None = None) -> None:
        self.outcome.append("abort")

    async def continue_(self) -> None:
        self.outcome.append("continue")


# Scenario: The rendered page cannot reach the network
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ["http://169.254.169.254/latest", _PUBLIC_URL, "https://cdn.example.com/a.png"],
)
async def test_every_page_request_is_aborted(url: str) -> None:
    route = _Route(_Request(url))
    await block_all_requests(route)
    assert route.outcome == ["abort"]


@pytest.mark.asyncio
async def test_verdicts_are_cached_per_host() -> None:
    calls: list[str] = []

    async def spy(host: str) -> tuple[str, ...]:
        calls.append(host)
        return ("93.184.216.34",)

    guard = ScrapeRouteGuard(spy)
    assert await guard.allows(_PUBLIC_URL) is True
    assert await guard.allows("https://news.example.com/other") is True
    assert await guard.allows("not a url") is False
    assert calls == ["news.example.com"]


class _Page:
    def __init__(self) -> None:
        self.handler: Callable[[_Route], Awaitable[None]] | None = None
        self.content: str | None = None
        self.navigated = False

    async def route(
        self, _pattern: str, handler: Callable[[_Route], Awaitable[None]]
    ) -> None:
        self.handler = handler

    async def goto(self, url: str, **_: object) -> None:
        self.navigated = True

    async def set_content(self, html: str, **_: object) -> None:
        assert self.handler is not None, "requests must be blocked before rendering"
        self.content = html

    async def inner_text(self, _selector: str) -> str:
        return "article text"


class _Browser:
    def __init__(self, page: _Page) -> None:
        self._page = page
        self.closed = False
        self.page_options: dict[str, object] = {}

    async def new_page(self, **options: object) -> _Page:
        self.page_options = options
        return self._page

    async def close(self) -> None:
        self.closed = True


class _Playwright:
    def __init__(self, browser: _Browser) -> None:
        self.chromium = self
        self._browser = browser
        self.launched = False

    async def launch(self, **_: object) -> _Browser:
        self.launched = True
        return self._browser

    async def __aenter__(self) -> _Playwright:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


def _patch(
    monkeypatch: pytest.MonkeyPatch, fake: _Playwright, fetched: list[str]
) -> None:
    import playwright.async_api as pw

    async def fetch(url: str) -> FetchedDocument:
        fetched.append(url)
        if not await url_safety.is_safe_url_target(url, _resolve):
            raise UnsafeResearchTargetError(url)
        return FetchedDocument(final_url=url, html=_HTML)

    monkeypatch.setattr(pw, "async_playwright", lambda: fake)
    monkeypatch.setattr(research_tool, "fetch_public_document", fetch)


# Scenario: The rendered page cannot reach the network
@pytest.mark.asyncio
async def test_scraper_renders_the_fetched_html_without_navigating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _Page()
    browser = _Browser(page)
    fetched: list[str] = []
    _patch(monkeypatch, _Playwright(browser), fetched)

    text = await research_tool.PlaywrightResearchTool.scrape_url(_PUBLIC_URL)

    assert text == "article text"
    assert fetched == [_PUBLIC_URL]
    assert page.navigated is False
    assert page.content == _HTML
    assert page.handler is block_all_requests
    assert browser.page_options.get("java_script_enabled") is False
    assert browser.closed is True


# Scenario: Unsafe first URL never launches the browser
@pytest.mark.asyncio
async def test_unsafe_first_url_never_launches_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _Playwright(_Browser(_Page()))
    fetched: list[str] = []
    _patch(monkeypatch, fake, fetched)

    with pytest.raises(UnsafeResearchTargetError):
        await research_tool.PlaywrightResearchTool.scrape_url(_REBOUND_URL)
    assert fake.launched is False
