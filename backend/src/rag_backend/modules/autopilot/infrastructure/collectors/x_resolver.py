"""X status enrichment. Off unless ``AUTOPILOT_X_RESOLVER=mirror``.

``NoneResolver`` performs no I/O. ``MirrorResolver`` GETs only the
configured mirror host and does not follow redirects, so the client
cannot be sent to x.com. A non-2xx response or a block page keeps the
search snippet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_backend.domain.constants.research_enrichment import (
    BLOCK_PAGE_MARKERS,
    BLOCK_PAGE_SCAN_CHARS,
)
from rag_backend.modules.autopilot.constants import SCHEME_HTTPS
from rag_backend.modules.autopilot.domain.signals import clip_text
from rag_backend.modules.autopilot.domain.x_status import XStatusTarget
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
    is_http_success,
)

_TAGS = re.compile(r"<[^>]+>")
_SCHEME_MARK = "://"


@dataclass(frozen=True, kw_only=True)
class MirrorResolverConfig:
    """Mirror host plus the HTTP client. The host is not a URL."""

    http: HttpGetter
    host: str


class NoneResolver:
    """Default resolver. Returns None without contacting x.com or a mirror."""

    def __init__(self) -> None:
        self.calls = 0

    async def resolve(self, target: XStatusTarget) -> str | None:
        """Keep the search snippet."""
        del target
        self.calls += 1
        return None


class MirrorResolver:
    """Fetch ``https://{host}/{handle}/status/{id}`` and return visible text."""

    def __init__(self, config: MirrorResolverConfig) -> None:
        self._config = config

    async def resolve(self, target: XStatusTarget) -> str | None:
        """Return mirror text, or None when the mirror is unusable."""
        url = mirror_url(self._config.host, target)
        if url is None:
            return None
        body = await self._body(url)
        if body is None or is_block_page(body):
            return None
        text = clip_text(strip_tags(body))
        if not text:
            return None
        return text

    async def _body(self, url: str) -> str | None:
        response = await self._config.http.get(
            HttpGet(url=url, follow_redirects=False),
        )
        if not is_http_success(response.status_code):
            return None
        return response.text


def mirror_url(host: str, target: XStatusTarget) -> str | None:
    """Build the mirror URL, or None when the host is empty or not a hostname."""
    cleaned = host.strip()
    if not cleaned or _SCHEME_MARK in cleaned or "/" in cleaned:
        return None
    return f"{SCHEME_HTTPS}://{cleaned}/{target.handle}/status/{target.status_id}"


def is_block_page(text: str) -> bool:
    """True when the body matches the research block-page markers."""
    head = text[:BLOCK_PAGE_SCAN_CHARS].lower()
    return any(marker in head for marker in BLOCK_PAGE_MARKERS)


def strip_tags(body: str) -> str:
    """Drop markup so a mirror HTML page becomes snippet-sized text."""
    return _TAGS.sub(" ", body)
