"""Redirect hops are checked before any request is sent (QA r2 R2).

A real HTTP server on 127.0.0.1 answers ``/start`` with a 302. The research
fetcher reaches ``/start`` through a public-looking name, and must refuse the
hop to ``127.0.0.1`` without ever requesting it. The server records every
path it served, so "no request reached the disallowed hop" is observed, not
assumed.

Feature: tests/features/url_safety_ssrf.feature
  Scenario: A redirect to an internal address is never requested
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from rag_backend.application.services.tools import research_fetch
from rag_backend.application.services.tools.research_fetch import (
    GuardedDocumentFetcher,
)
from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
)
from rag_backend.domain.constants.url_safety import RESEARCH_MAX_REDIRECTS

_PUBLIC_HOST = "public.example.com"
_PUBLIC_IP = "93.184.216.34"
_LOOPBACK = "127.0.0.1"
_FINAL_HTML = "<html><body><p>public article</p></body></html>"


@dataclass
class _Hits:
    paths: list[str] = field(default_factory=list)


def _handler_for(hits: _Hits, port_box: list[int]) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            hits.paths.append(self.path)
            port = port_box[0]
            routes = {
                "/start": f"http://{_LOOPBACK}:{port}/internal",
                "/to-public": f"http://{_PUBLIC_HOST}:{port}/final",
                "/to-relative": "/final",
            }
            if self.path in routes:
                self.send_response(302)
                self.send_header("Location", routes[self.path])
                self.end_headers()
                return
            if self.path.startswith("/loop"):
                self.send_response(302)
                self.send_header("Location", f"/loop{len(hits.paths)}")
                self.end_headers()
                return
            body = _FINAL_HTML.encode()
            if self.path == "/internal":
                body = b"secret metadata"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            del fmt, args

    return _Handler


@dataclass(frozen=True)
class _Server:
    port: int
    hits: _Hits


@pytest.fixture
def server() -> Iterator[_Server]:
    hits = _Hits()
    port_box: list[int] = [0]
    httpd = ThreadingHTTPServer((_LOOPBACK, 0), _handler_for(hits, port_box))
    port_box[0] = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield _Server(port=port_box[0], hits=hits)
    finally:
        httpd.shutdown()
        httpd.server_close()


class _PublicNameToLoopback(httpx.AsyncBaseTransport):
    """Sends ``public.example.com`` traffic to the local server.

    The guard sees the public name (resolved by the fake resolver to a
    public IP); only the socket goes to 127.0.0.1. Any request for a
    literal 127.0.0.1 URL is sent unchanged, so it would reach the server.
    """

    def __init__(self) -> None:
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == _PUBLIC_HOST:
            request.url = request.url.copy_with(host=_LOOPBACK)
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


async def _resolve(host: str) -> tuple[str, ...]:
    if host == _PUBLIC_HOST:
        return (_PUBLIC_IP,)
    return ("10.0.0.9",)


def _fetcher() -> GuardedDocumentFetcher:
    client = httpx.AsyncClient(
        transport=_PublicNameToLoopback(), follow_redirects=False, trust_env=False
    )
    return GuardedDocumentFetcher(ScrapeRouteGuard(_resolve), client)


# Scenario: A redirect to an internal address is never requested
@pytest.mark.asyncio
async def test_redirect_to_loopback_is_refused_before_it_is_requested(
    server: _Server,
) -> None:
    with pytest.raises(UnsafeResearchTargetError):
        await _fetcher().fetch(f"http://{_PUBLIC_HOST}:{server.port}/start")

    assert server.hits.paths == ["/start"]


@pytest.mark.asyncio
async def test_public_redirect_chain_is_followed_hop_by_hop(server: _Server) -> None:
    document = await _fetcher().fetch(f"http://{_PUBLIC_HOST}:{server.port}/to-public")

    assert server.hits.paths == ["/to-public", "/final"]
    assert document.final_url == f"http://{_PUBLIC_HOST}:{server.port}/final"
    assert "public article" in document.html


@pytest.mark.asyncio
async def test_relative_location_is_resolved_and_checked(server: _Server) -> None:
    document = await _fetcher().fetch(
        f"http://{_PUBLIC_HOST}:{server.port}/to-relative"
    )

    assert server.hits.paths == ["/to-relative", "/final"]
    assert document.final_url.endswith("/final")


@pytest.mark.asyncio
async def test_more_than_five_redirects_are_refused(server: _Server) -> None:
    with pytest.raises(UnsafeResearchTargetError):
        await _fetcher().fetch(f"http://{_PUBLIC_HOST}:{server.port}/loop")

    assert len(server.hits.paths) == RESEARCH_MAX_REDIRECTS + 1


@pytest.mark.asyncio
async def test_body_is_read_up_to_the_byte_cap(
    server: _Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(research_fetch, "RESEARCH_FETCH_MAX_BYTES", 10)

    document = await _fetcher().fetch(f"http://{_PUBLIC_HOST}:{server.port}/final")

    assert document.html == _FINAL_HTML[:10]


@pytest.mark.asyncio
async def test_production_fetch_refuses_an_internal_url_without_a_request() -> None:
    with pytest.raises(UnsafeResearchTargetError):
        await research_fetch.fetch_public_document("http://10.0.0.1/admin")


@pytest.mark.asyncio
async def test_production_client_follows_nothing_and_ignores_the_environment() -> None:
    async with research_fetch.research_http_client() as client:
        assert client.follow_redirects is False
        assert client.trust_env is False
