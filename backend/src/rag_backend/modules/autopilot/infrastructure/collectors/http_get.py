"""HTTP GET used by every collector except the X web search.

``trust_env`` is off so a developer proxy cannot redirect a test or a
scout run. Callers choose whether redirects are followed. The mirror
resolver does not follow them, so a mirror cannot bounce the client to x.com.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from rag_backend.modules.autopilot.constants import (
    HEADER_USER_AGENT,
    HTTP_SUCCESS_MAX,
    HTTP_SUCCESS_MIN,
    HTTP_USER_AGENT,
)


@dataclass(frozen=True, kw_only=True)
class HttpGet:
    """One GET. Params and headers are tuples so the value stays hashable."""

    url: str
    params: tuple[tuple[str, str], ...] = ()
    headers: tuple[tuple[str, str], ...] = ()
    follow_redirects: bool = True


@dataclass(frozen=True, kw_only=True)
class HttpText:
    """The status and body of one GET. Transport errors propagate."""

    status_code: int
    text: str


class HttpGetter(Protocol):
    """Outbound GET. Tests substitute a fake or let respx mock httpx."""

    async def get(self, request: HttpGet) -> HttpText:
        """Perform the GET."""
        ...


def is_http_success(status_code: int) -> bool:
    """True for 2xx responses. 451 and other non-2xx are failures."""
    return HTTP_SUCCESS_MIN <= status_code < HTTP_SUCCESS_MAX


class HttpxGetter:
    """httpx adapter. A new client per call keeps timeouts local to the request."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    async def get(self, request: HttpGet) -> HttpText:
        """GET ``request.url`` and return the status and body."""
        headers = {HEADER_USER_AGENT: HTTP_USER_AGENT}
        headers.update(dict(request.headers))
        async with httpx.AsyncClient(timeout=self._timeout, trust_env=False) as client:
            response = await client.get(
                request.url,
                params=dict(request.params),
                headers=headers,
                follow_redirects=request.follow_redirects,
            )
        return HttpText(status_code=response.status_code, text=response.text)
