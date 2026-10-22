"""Shared JSON fetch used by the autopilot collectors.

Scenario: a 2xx JSON body is returned parsed.
Scenario: a non-2xx status raises UpstreamError.
Scenario: an unparsable body raises UpstreamError.
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.fetch_json import (
    fetch_json,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpText,
)

_REQUEST = HttpGet(url="https://example.com/feed")


class _Getter:
    def __init__(self, status_code: int, text: str) -> None:
        self._reply = HttpText(status_code=status_code, text=text)
        self.requests: list[HttpGet] = []

    async def get(self, request: HttpGet) -> HttpText:
        self.requests.append(request)
        return self._reply


# Scenario: a 2xx JSON body is returned parsed.
async def test_returns_parsed_body_and_forwards_the_request() -> None:
    getter = _Getter(200, '{"hits": [1]}')

    assert await fetch_json(getter, _REQUEST) == {"hits": [1]}
    assert getter.requests == [_REQUEST]


# Scenario: a non-2xx status raises UpstreamError.
async def test_non_success_status_raises_upstream_error() -> None:
    with pytest.raises(UpstreamError):
        await fetch_json(_Getter(451, "{}"), _REQUEST)


# Scenario: an unparsable body raises UpstreamError.
async def test_unparsable_body_raises_upstream_error() -> None:
    with pytest.raises(UpstreamError):
        await fetch_json(_Getter(200, "not json"), _REQUEST)
