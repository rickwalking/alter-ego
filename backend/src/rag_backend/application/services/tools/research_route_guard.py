"""Per-request SSRF guard for the Playwright research scraper (QA r1 S-W1).

The first URL is checked before the browser starts, but a public page can
redirect to ``http://169.254.169.254/`` or a docker service, and a page can load
sub-resources from anywhere. This guard is installed with ``page.route`` so every
request the page makes, including redirect hops, is re-checked with the domain
rules (scheme, internal names, and every DNS answer). Disallowed requests are
aborted.

``page.on("request")`` also records every request. A redirect hop the browser
followed without routing it is caught there, and the scrape is refused after
navigation so its content never reaches research.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from rag_backend.domain.constants.url_safety import (
    ERR_UNSAFE_REDIRECT,
    LOG_URL_BLOCKED,
    SKIPPED_RESOURCE_TYPES,
)
from rag_backend.domain.url_safety import HostResolver, is_safe_url_target, url_host

logger = structlog.get_logger()


class GuardedRequest(Protocol):
    """The request fields the guard reads."""

    @property
    def url(self) -> str:
        """Absolute request URL."""
        ...

    @property
    def resource_type(self) -> str:
        """Playwright resource type, e.g. ``document`` or ``image``."""
        ...


class GuardedRoute(Protocol):
    """The route operations the guard calls."""

    @property
    def request(self) -> GuardedRequest:
        """The intercepted request."""
        ...

    async def abort(self) -> None:
        """Fail the request with Playwright's default error code."""
        ...

    async def continue_(self) -> None:
        """Send the request unchanged."""
        ...


class UnsafeResearchTargetError(ValueError):
    """The scrape touched a URL the SSRF guard refuses."""


class ScrapeRouteGuard:
    """Checks each request once per host and remembers what it refused."""

    def __init__(self, resolver: HostResolver | None = None) -> None:
        self._resolver = resolver
        self._verdicts: dict[str, bool] = {}
        self.blocked: list[str] = []
        self.seen: list[str] = []

    async def allows(self, url: str) -> bool:
        """True when ``url`` passes the domain SSRF rules. Cached per host."""
        key = url_host(url)
        if key is None:
            return False
        cached = self._verdicts.get(key)
        if cached is not None:
            return cached
        verdict = await is_safe_url_target(url, self._resolver)
        self._verdicts[key] = verdict
        return verdict

    async def handle(self, route: GuardedRoute) -> None:
        """``page.route`` handler: abort disallowed hops and unneeded assets."""
        request = route.request
        if request.resource_type in SKIPPED_RESOURCE_TYPES:
            await route.abort()
            return
        if await self.allows(request.url):
            await route.continue_()
            return
        self.blocked.append(request.url)
        logger.warning(LOG_URL_BLOCKED, url=request.url)
        await route.abort()

    def record(self, request: GuardedRequest) -> None:
        """``page.on("request")`` listener: remember every URL the page asked for."""
        if request.resource_type in SKIPPED_RESOURCE_TYPES:
            return
        self.seen.append(request.url)

    async def verify(self, final_url: str) -> None:
        """Raise when any hop, or the final URL, is not allowed."""
        if self.blocked:
            raise UnsafeResearchTargetError(ERR_UNSAFE_REDIRECT)
        for url in (*self.seen, final_url):
            if not await self.allows(url):
                logger.warning(LOG_URL_BLOCKED, url=url)
                raise UnsafeResearchTargetError(ERR_UNSAFE_REDIRECT)


__all__ = [
    "GuardedRequest",
    "GuardedRoute",
    "ScrapeRouteGuard",
    "UnsafeResearchTargetError",
]
