"""Fetch a research document hop by hop, checking every hop first (QA r2 R2).

``httpx`` runs with ``follow_redirects=False`` and ``trust_env=False`` (no
proxy from the environment). Each URL, the first one and every ``Location``
target, passes ``ScrapeRouteGuard.allows`` (scheme, internal names, every DNS
answer) before it is requested, so a redirect to ``127.0.0.1``, the metadata
service or a docker service is refused without being sent. At most five
redirects are followed. The body is read up to a byte cap.

Parity with the old Chromium navigation (QA r3 Q5):

* One overall deadline of 15 s covers the whole fetch, every hop included.
* Only ``text/html``, ``application/xhtml+xml`` and ``text/plain`` are read.
  Anything else (PDF, images, binary) raises
  ``UnsupportedResearchContentError``; every caller already treats a failed
  scrape as "skip this source", as it did when Chromium failed on a download.
* Requests carry a realistic browser User-Agent, Accept and Accept-Language.
* The charset is the header's, else the page's ``<meta charset>`` /
  ``http-equiv``, else UTF-8 with undecodable bytes replaced.
* JavaScript never runs: a page that builds its text with JavaScript comes
  back as its static HTML. This is accepted.

Residual risk: DNS rebinding between the guard's lookup and the socket's own
lookup. The window is one request long; see ``domain/url_safety.py``.
"""

from __future__ import annotations

import asyncio
import codecs
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import structlog

from rag_backend.application.services.tools.research_route_guard import (
    ScrapeRouteGuard,
    UnsafeResearchTargetError,
)
from rag_backend.domain.constants.url_safety import (
    DECODE_ERRORS,
    ERR_TOO_MANY_REDIRECTS,
    ERR_UNSAFE_REDIRECT,
    ERR_UNSUPPORTED_CONTENT,
    HEADER_CONTENT_TYPE,
    HEADER_LOCATION,
    HTTP_METHOD_GET,
    LOG_URL_BLOCKED,
    LOG_URL_UNSUPPORTED,
    MEDIA_TYPE_PARAM_SEPARATOR,
    MEDIA_TYPE_TEXT_HTML,
    META_CHARSET_PATTERN,
    META_CHARSET_SCAN_BYTES,
    META_SCAN_ENCODING,
    REDIRECT_STATUSES,
    RESEARCH_FETCH_DEADLINE_SECONDS,
    RESEARCH_FETCH_MAX_BYTES,
    RESEARCH_FETCH_TIMEOUT_SECONDS,
    RESEARCH_MAX_REDIRECTS,
    RESEARCH_REQUEST_HEADERS,
    RESEARCH_TEXT_MEDIA_TYPES,
    RESOURCE_HINT_PATTERN,
    TEXT_ENCODING_FALLBACK,
)

logger = structlog.get_logger()

_META_CHARSET = re.compile(META_CHARSET_PATTERN, re.IGNORECASE)
_RESOURCE_HINT = re.compile(RESOURCE_HINT_PATTERN, re.IGNORECASE)


class UnsupportedResearchContentError(Exception):
    """The document is not text (PDF, image, binary): skip this source."""


@dataclass(frozen=True, kw_only=True)
class FetchedDocument:
    """The text at the end of a checked redirect chain."""

    final_url: str
    html: str
    media_type: str = MEDIA_TYPE_TEXT_HTML


@dataclass(frozen=True, kw_only=True)
class _Hop:
    """One response: a redirect target, or the final body."""

    location: str | None
    body: str
    media_type: str = MEDIA_TYPE_TEXT_HTML


class GuardedDocumentFetcher:
    """Follows redirects itself so no unchecked hop is ever requested."""

    def __init__(self, guard: ScrapeRouteGuard, client: httpx.AsyncClient) -> None:
        self._guard = guard
        self._client = client

    async def fetch(self, url: str) -> FetchedDocument:
        """Fetch ``url`` within the overall deadline (``TimeoutError`` after).

        Raises ``UnsafeResearchTargetError`` on a refused hop and
        ``UnsupportedResearchContentError`` on a non-text document.
        """
        async with asyncio.timeout(RESEARCH_FETCH_DEADLINE_SECONDS):
            return await self._follow(url)

    async def _follow(self, url: str) -> FetchedDocument:
        current = url
        for _hop in range(RESEARCH_MAX_REDIRECTS + 1):
            await self._require_allowed(current)
            hop = await self._get(current)
            if hop.location is None:
                return FetchedDocument(
                    final_url=current, html=hop.body, media_type=hop.media_type
                )
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
            media_type = _require_text(url, response)
            body = await _read_capped(response)
        return _Hop(location=None, body=body, media_type=media_type)


def _require_text(url: str, response: httpx.Response) -> str:
    raw = response.headers.get(HEADER_CONTENT_TYPE, "")
    media_type = raw.split(MEDIA_TYPE_PARAM_SEPARATOR)[0].strip().lower()
    if media_type in RESEARCH_TEXT_MEDIA_TYPES:
        return media_type
    logger.warning(LOG_URL_UNSUPPORTED, url=url, content_type=raw)
    raise UnsupportedResearchContentError(ERR_UNSUPPORTED_CONTENT)


def strip_resource_hints(html: str) -> str:
    """Drop ``<link rel=dns-prefetch|preconnect|prefetch|preload|prerender>`` (Q6)."""
    return _RESOURCE_HINT.sub("", html)


def _decode(raw: bytes, header_charset: str | None) -> str:
    """Header charset, else the page's ``<meta>``, else UTF-8 (replacing)."""
    for label in (header_charset, _meta_charset(raw)):
        codec = _codec(label)
        if codec is not None:
            return raw.decode(codec, errors=DECODE_ERRORS)
    return raw.decode(TEXT_ENCODING_FALLBACK, errors=DECODE_ERRORS)


def _meta_charset(raw: bytes) -> str | None:
    head = raw[:META_CHARSET_SCAN_BYTES].decode(META_SCAN_ENCODING, errors="ignore")
    match = _META_CHARSET.search(head)
    return None if match is None else match.group(1)


def _codec(label: str | None) -> str | None:
    if not label:
        return None
    try:
        return codecs.lookup(label).name
    except LookupError:
        return None


async def _read_capped(response: httpx.Response) -> str:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= RESEARCH_FETCH_MAX_BYTES:
            break
    raw = b"".join(chunks)[:RESEARCH_FETCH_MAX_BYTES]
    return _decode(raw, response.charset_encoding)


def research_http_client() -> httpx.AsyncClient:
    """No redirects, no proxy or CA settings from the environment."""
    return httpx.AsyncClient(
        follow_redirects=False,
        trust_env=False,
        timeout=RESEARCH_FETCH_TIMEOUT_SECONDS,
        headers=RESEARCH_REQUEST_HEADERS,
    )


async def fetch_public_document(url: str) -> FetchedDocument:
    """Production fetch: system DNS, a fresh client per scrape."""
    async with research_http_client() as client:
        return await GuardedDocumentFetcher(ScrapeRouteGuard(), client).fetch(url)


__all__ = [
    "FetchedDocument",
    "GuardedDocumentFetcher",
    "UnsupportedResearchContentError",
    "fetch_public_document",
    "research_http_client",
    "strip_resource_hints",
]
