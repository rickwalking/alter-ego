"""Fetch a research document hop by hop, checking every hop first (QA r2 R2).

``httpx`` runs with ``follow_redirects=False`` and ``trust_env=False`` (no
proxy from the environment). Each URL, the first one and every ``Location``
target, passes ``ScrapeRouteGuard.allows`` (scheme, internal names, every DNS
answer) before it is requested, so a redirect to ``127.0.0.1``, the metadata
service or a docker service is refused without being sent. At most five
redirects are followed. The body is read up to a byte cap.

Residual risk: DNS rebinding between the guard's lookup and the socket's own
lookup. The window is one request long; see ``domain/url_safety.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import structlog

from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
)
from rag_backend.domain.constants.url_safety import (
    ERR_TOO_MANY_REDIRECTS,
    ERR_UNSAFE_REDIRECT,
    HEADER_LOCATION,
    HTTP_METHOD_GET,
    LOG_URL_BLOCKED,
    REDIRECT_STATUSES,
    RESEARCH_FETCH_MAX_BYTES,
    RESEARCH_FETCH_TIMEOUT_SECONDS,
    RESEARCH_MAX_REDIRECTS,
    TEXT_ENCODING_FALLBACK,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class FetchedDocument:
    """The HTML at the end of a checked redirect chain."""

    final_url: str
    html: str


@dataclass(frozen=True, kw_only=True)
class _Hop:
    """One response: a redirect target, or the final body."""

    location: str | None
    body: str


class GuardedDocumentFetcher:
    """Follows redirects itself so no unchecked hop is ever requested."""

    def __init__(self, guard: ScrapeRouteGuard, client: httpx.AsyncClient) -> None:
        self._guard = guard
        self._client = client

    async def fetch(self, url: str) -> FetchedDocument:
        """Fetch ``url``. Raises ``UnsafeResearchTargetError`` on a refused hop."""
        current = url
        for _hop in range(RESEARCH_MAX_REDIRECTS + 1):
            await self._require_allowed(current)
            hop = await self._get(current)
            if hop.location is None:
                return FetchedDocument(final_url=current, html=hop.body)
            current = urljoin(current, hop.location)
        logger.warning(LOG_URL_BLOCKED, url=current, reason=ERR_TOO_MANY_REDIRECTS)
        raise UnsafeResearchTargetError(ERR_TOO_MANY_REDIRECTS)

    async def _require_allowed(self, url: str) -> None:
        if await self._guard.allows(url):
            return
        logger.warning(LOG_URL_BLOCKED, url=url)
        raise UnsafeResearchTargetError(ERR_UNSAFE_REDIRECT)

    async def _get(self, url: str) -> _Hop:
        async with self._client.stream(HTTP_METHOD_GET, url) as response:
            location = response.headers.get(HEADER_LOCATION)
            if response.status_code in REDIRECT_STATUSES and location:
                return _Hop(location=location, body="")
            body = await _read_capped(response)
        return _Hop(location=None, body=body)


async def _read_capped(response: httpx.Response) -> str:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= RESEARCH_FETCH_MAX_BYTES:
            break
    raw = b"".join(chunks)[:RESEARCH_FETCH_MAX_BYTES]
    encoding = response.encoding or TEXT_ENCODING_FALLBACK
    return raw.decode(encoding, errors="replace")


def research_http_client() -> httpx.AsyncClient:
    """No redirects, no proxy or CA settings from the environment."""
    return httpx.AsyncClient(
        follow_redirects=False,
        trust_env=False,
        timeout=RESEARCH_FETCH_TIMEOUT_SECONDS,
    )


async def fetch_public_document(url: str) -> FetchedDocument:
    """Production fetch: system DNS, a fresh client per scrape."""
    async with research_http_client() as client:
        return await GuardedDocumentFetcher(ScrapeRouteGuard(), client).fetch(url)


__all__ = [
    "FetchedDocument",
    "GuardedDocumentFetcher",
    "fetch_public_document",
    "research_http_client",
]
