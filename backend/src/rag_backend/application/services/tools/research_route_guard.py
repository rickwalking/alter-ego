"""SSRF guard for the Playwright research scraper (QA r1 S-W1, QA r2 R2).

Playwright does not pass redirect hops through ``page.route``, so a guard on
the browser cannot stop a blind GET to ``http://169.254.169.254/`` or a
docker service. The browser therefore never touches the network:

* ``ScrapeRouteGuard.allows`` checks one URL with the domain rules (scheme,
  internal names, every DNS answer). ``GuardedDocumentFetcher`` calls it on
  the first URL and on every redirect hop *before* that hop is requested.
* ``block_all_requests`` is installed with ``page.route`` while the fetched
  HTML is rendered with ``page.set_content``, so sub-resources, scripts and
  navigations from the page are all aborted.
"""

from __future__ import annotations

from typing import Protocol

from rag_backend.domain.url_safety import HostResolver, is_safe_url_target, url_host


class GuardedRequest(Protocol):
    """The request fields the guard reads."""

    @property
    def url(self) -> str:
        """Absolute request URL."""
        ...


class GuardedRoute(Protocol):
    """The route operation the guard calls."""

    @property
    def request(self) -> GuardedRequest:
        """The intercepted request."""
        ...

    async def abort(self) -> None:
        """Fail the request with Playwright's default error code."""
        ...


class UnsafeResearchTargetError(ValueError):
    """The scrape touched a URL the SSRF guard refuses."""


class ScrapeRouteGuard:
    """Checks URLs with the domain SSRF rules, once per host."""

    def __init__(self, resolver: HostResolver | None = None) -> None:
        self._resolver = resolver
        self._verdicts: dict[str, bool] = {}

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


async def block_all_requests(route: GuardedRoute) -> None:
    """``page.route`` handler for rendered HTML: no request leaves the browser."""
    await route.abort()


__all__ = [
    "GuardedRequest",
    "GuardedRoute",
    "ScrapeRouteGuard",
    "UnsafeResearchTargetError",
    "block_all_requests",
]
