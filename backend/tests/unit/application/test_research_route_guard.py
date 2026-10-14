"""Playwright route guard re-checks every hop (QA r1 S-W1).

Feature: tests/features/url_safety_ssrf.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from rag_backend.application.services.tools import research_tool
from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
)
from rag_backend.domain import url_safety

_PUBLIC_URL = "https://news.example.com/story"
_METADATA_URL = "http://169.254.169.254/latest"
_REBOUND_URL = "https://rebind.example.net/x"


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


# Scenario: Redirect hop to an internal address is aborted
@pytest.mark.asyncio
async def test_redirect_hop_to_metadata_is_aborted() -> None:
    guard = ScrapeRouteGuard(_resolve)
    first = _Route(_Request(_PUBLIC_URL))
    hop = _Route(_Request(_METADATA_URL))

    await guard.handle(first)
    await guard.handle(hop)

    assert first.outcome == ["continue"]
    assert hop.outcome == ["abort"]
    assert guard.blocked == [_METADATA_URL]
    with pytest.raises(UnsafeResearchTargetError):
        await guard.verify(_PUBLIC_URL)


@pytest.mark.asyncio
async def test_assets_are_aborted_without_dns() -> None:
    calls: list[str] = []

    async def spy(host: str) -> tuple[str, ...]:
        calls.append(host)
        return ("93.184.216.34",)

    guard = ScrapeRouteGuard(spy)
    image = _Route(_Request("https://cdn.example.com/a.png", "image"))
    await guard.handle(image)
    guard.record(_Request("https://cdn.example.com/b.png", "image"))

    assert image.outcome == ["abort"]
    assert calls == []
    assert guard.seen == []


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


# Scenario: Redirect hop the browser did not route is still refused
@pytest.mark.asyncio
async def test_unrouted_hop_is_refused_after_navigation() -> None:
    guard = ScrapeRouteGuard(_resolve)
    guard.record(_Request(_PUBLIC_URL))
    guard.record(_Request(_REBOUND_URL))

    with pytest.raises(UnsafeResearchTargetError):
        await guard.verify(_PUBLIC_URL)


@pytest.mark.asyncio
async def test_clean_navigation_verifies() -> None:
    guard = ScrapeRouteGuard(_resolve)
    guard.record(_Request(_PUBLIC_URL))
    await guard.verify(_PUBLIC_URL)
    with pytest.raises(UnsafeResearchTargetError):
        await guard.verify(_REBOUND_URL)


class _Page:
    def __init__(self, redirect_to: str) -> None:
        self.url = ""
        self._redirect_to = redirect_to
        self._handler: object = None
        self._listener: object = None

    async def route(self, _pattern: str, handler: object) -> None:
        self._handler = handler

    def on(self, _event: str, listener: object) -> None:
        self._listener = listener

    async def goto(self, url: str, **_: object) -> None:
        for hop in (url, self._redirect_to):
            request = _Request(hop)
            self._listener(request)  # type: ignore[operator]
            route = _Route(request)
            await self._handler(route)  # type: ignore[operator]
            if route.outcome == ["abort"]:
                return
            self.url = hop

    async def inner_text(self, _selector: str) -> str:
        return "secret metadata"


class _Browser:
    def __init__(self, page: _Page) -> None:
        self._page = page
        self.closed = False

    async def new_page(self) -> _Page:
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


def _patch(monkeypatch: pytest.MonkeyPatch, fake: _Playwright) -> None:
    import playwright.async_api as pw

    monkeypatch.setattr(pw, "async_playwright", lambda: fake)
    monkeypatch.setattr(url_safety, "system_resolve", _resolve)


# Scenario: Redirect hop to an internal address is aborted
@pytest.mark.asyncio
async def test_scraper_refuses_page_that_redirects_to_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser = _Browser(_Page(_METADATA_URL))
    _patch(monkeypatch, _Playwright(browser))

    with pytest.raises(UnsafeResearchTargetError):
        await research_tool.PlaywrightResearchTool.scrape_url(_PUBLIC_URL)
    assert browser.closed is True


@pytest.mark.asyncio
async def test_scraper_returns_text_for_public_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser = _Browser(_Page("https://news.example.com/final"))
    _patch(monkeypatch, _Playwright(browser))

    text = await research_tool.PlaywrightResearchTool.scrape_url(_PUBLIC_URL)
    assert text == "secret metadata"


# Scenario: Unsafe first URL never launches the browser
@pytest.mark.asyncio
async def test_unsafe_first_url_never_launches_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _Playwright(_Browser(_Page(_PUBLIC_URL)))
    _patch(monkeypatch, fake)

    with pytest.raises(UnsafeResearchTargetError):
        await research_tool.PlaywrightResearchTool.scrape_url(_REBOUND_URL)
    assert fake.launched is False
