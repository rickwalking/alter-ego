"""Research fetch parity with the old Chromium scrape (QA r3 Q5, Q6).

The fetch has one overall deadline, renders only text documents, looks like
a browser, decodes by header / meta charset, and the rendered HTML can never
make Chromium resolve or connect to a host.

Feature: tests/features/url_safety_ssrf.feature
  Scenario: A research fetch ends at one overall deadline
  Scenario: Only text documents are rendered
  Scenario: The fetch sends browser headers and honours the page charset
  Scenario: Resource hints in the page never reach the network
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx
import pytest

from rag_backend.agents import research_enrichment
from rag_backend.application.services.tools import research_fetch, research_tool
from rag_backend.application.services.tools.research_fetch import (
    FetchedDocument,
    GuardedDocumentFetcher,
    UnsupportedResearchContentError,
    research_http_client,
    strip_resource_hints,
)
from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
)
from rag_backend.domain.constants.url_safety import (
    CHROMIUM_DISABLE_DNS_PREFETCH,
    MEDIA_TYPE_TEXT_PLAIN,
    RESEARCH_REQUEST_HEADERS,
)
from tests.unit.application.test_research_route_guard import (
    _Browser,
    _Page,
    _Playwright,
)

_BASE = "https://news.example.com"
_Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


async def _public(host: str) -> tuple[str, ...]:
    del host
    return ("93.184.216.34",)


def _fetcher(handler: _Handler) -> GuardedDocumentFetcher:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
    )
    return GuardedDocumentFetcher(ScrapeRouteGuard(_public), client)


def _body(content: bytes, content_type: str | None) -> _Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        headers = {} if content_type is None else {"content-type": content_type}
        return httpx.Response(200, content=content, headers=headers)

    return handler


# Scenario: A research fetch ends at one overall deadline
@pytest.mark.asyncio
async def test_slow_hops_together_hit_the_overall_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(research_fetch, "RESEARCH_FETCH_DEADLINE_SECONDS", 0.25)
    paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        await asyncio.sleep(0.1)
        return httpx.Response(302, headers={"location": f"/hop{len(paths)}"})

    with pytest.raises(TimeoutError):
        await _fetcher(handler).fetch(f"{_BASE}/start")
    assert 2 <= len(paths) <= 3


def test_the_deadline_is_15_seconds() -> None:
    assert research_fetch.RESEARCH_FETCH_DEADLINE_SECONDS == 15.0


# Scenario: Only text documents are rendered
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type",
    ["application/pdf", "image/png", "application/octet-stream", None],
)
async def test_non_text_documents_are_skipped(content_type: str | None) -> None:
    fetcher = _fetcher(_body(b"%PDF-1.7 binary", content_type))

    with pytest.raises(UnsupportedResearchContentError):
        await fetcher.fetch(f"{_BASE}/file")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "media_type"),
    [
        ("text/html; charset=utf-8", "text/html"),
        ("Application/XHTML+XML", "application/xhtml+xml"),
        ("text/plain", "text/plain"),
    ],
)
async def test_text_documents_are_fetched(content_type: str, media_type: str) -> None:
    document = await _fetcher(_body(b"<p>hi</p>", content_type)).fetch(f"{_BASE}/a")

    assert document.media_type == media_type
    assert document.html == "<p>hi</p>"


@pytest.mark.asyncio
async def test_a_skipped_document_keeps_the_original_research_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def refuse(url: str) -> FetchedDocument:
        raise UnsupportedResearchContentError(url)

    fake = _Playwright(_Browser(_Page()))
    _patch_browser(monkeypatch, fake)
    monkeypatch.setattr(research_tool, "fetch_public_document", refuse)

    scraped = await research_enrichment._scrape_one(
        f"{_BASE}/paper.pdf",
        research_tool.PlaywrightResearchTool(),
        asyncio.Semaphore(1),
    )

    assert scraped is None
    assert fake.launched is False


@pytest.mark.asyncio
async def test_plain_text_is_returned_without_chromium(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def plain(url: str) -> FetchedDocument:
        return FetchedDocument(
            final_url=url, html="a < b plain notes", media_type=MEDIA_TYPE_TEXT_PLAIN
        )

    fake = _Playwright(_Browser(_Page()))
    _patch_browser(monkeypatch, fake)
    monkeypatch.setattr(research_tool, "fetch_public_document", plain)

    text = await research_tool.PlaywrightResearchTool.scrape_url(f"{_BASE}/notes.txt")

    assert text == "a < b plain notes"
    assert fake.launched is False


# Scenario: The fetch sends browser headers and honours the page charset
@pytest.mark.asyncio
async def test_the_production_client_sends_browser_headers() -> None:
    async with research_http_client() as client:
        for name, value in RESEARCH_REQUEST_HEADERS.items():
            assert client.headers[name] == value
    assert RESEARCH_REQUEST_HEADERS["user-agent"].startswith("Mozilla/5.0")
    assert "text/html" in RESEARCH_REQUEST_HEADERS["accept"]
    assert RESEARCH_REQUEST_HEADERS["accept-language"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "content_type", "expected"),
    [
        ("café".encode("latin-1"), "text/html; charset=iso-8859-1", "café"),
        (
            b'<meta charset="windows-1252"><p>caf\xe9</p>',
            "text/html",
            '<meta charset="windows-1252"><p>café</p>',
        ),
        (
            b'<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">'
            b"caf\xe9",
            "text/html",
            '<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">'
            "café",
        ),
        ("café".encode(), "text/html", "café"),
        (b"caf\xe9", "text/html", "caf�"),
        (b'<meta charset="no-such-codec">caf\xe9', "text/html", None),
    ],
)
async def test_the_page_charset_is_honoured(
    content: bytes, content_type: str, expected: str | None
) -> None:
    document = await _fetcher(_body(content, content_type)).fetch(f"{_BASE}/c")

    if expected is None:
        assert document.html.endswith("caf�")
        return
    assert document.html == expected


# Scenario: Resource hints in the page never reach the network
def test_resource_hints_are_stripped_and_other_links_kept() -> None:
    html = (
        "<head>"
        '<link rel="dns-prefetch" href="//evil.example">'
        "<LINK REL=preconnect href=https://evil.example>"
        "<link href='https://evil.example/a.js' rel='prefetch'>"
        '<link rel="preload" as="script" href="/x.js">'
        '<link rel="prerender" href="https://evil.example/next">'
        '<link rel="stylesheet" href="/site.css">'
        "</head><body>text</body>"
    )

    cleaned = strip_resource_hints(html)

    assert "evil.example" not in cleaned
    assert "preload" not in cleaned
    assert '<link rel="stylesheet" href="/site.css">' in cleaned
    assert "<body>text</body>" in cleaned


@pytest.mark.asyncio
async def test_chromium_runs_without_dns_prefetch_on_stripped_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = '<link rel="dns-prefetch" href="//evil.example"><body>article</body>'

    async def fetch(url: str) -> FetchedDocument:
        return FetchedDocument(final_url=url, html=html)

    page = _Page()
    fake = _LaunchRecorder(_Browser(page))
    _patch_browser(monkeypatch, fake)
    monkeypatch.setattr(research_tool, "fetch_public_document", fetch)

    await research_tool.PlaywrightResearchTool.scrape_url(f"{_BASE}/story")

    assert CHROMIUM_DISABLE_DNS_PREFETCH in fake.args
    assert page.content is not None
    assert "evil.example" not in page.content


class _LaunchRecorder(_Playwright):
    def __init__(self, browser: _Browser) -> None:
        super().__init__(browser)
        self.args: list[str] = []

    async def launch(self, **options: object) -> _Browser:
        args = options.get("args")
        if isinstance(args, list):
            self.args = [str(arg) for arg in args]
        return await super().launch(**options)


def _patch_browser(monkeypatch: pytest.MonkeyPatch, fake: _Playwright) -> None:
    import playwright.async_api as pw

    monkeypatch.setattr(pw, "async_playwright", lambda: fake)
