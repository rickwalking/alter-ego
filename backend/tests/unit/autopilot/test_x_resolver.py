"""Mirror and none resolvers.

Gherkin: tests/features/autopilot_signals.feature
  Scenario: Mirror resolver falls back on legal block
"""

from __future__ import annotations

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.domain.x_status import XStatusTarget
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.x_resolver import (
    MirrorResolver,
    MirrorResolverConfig,
    NoneResolver,
    mirror_url,
)

_TARGET = XStatusTarget(
    handle="bob",
    status_id="99",
    canonical_url="https://x.com/bob/status/99",
)
_MIRROR = "https://mirror.example/bob/status/99"


def _resolver(host: str = "mirror.example") -> MirrorResolver:
    return MirrorResolver(MirrorResolverConfig(http=HttpxGetter(5.0), host=host))


# Scenario: Mirror resolver falls back on legal block
@pytest.mark.asyncio
async def test_http_451_returns_nothing() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(_MIRROR).mock(return_value=httpx.Response(451, text="nope"))
        assert await _resolver().resolve(_TARGET) is None
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_block_page_returns_nothing() -> None:
    body = "<html><title>Just a moment...</title><p>checking your browser</p></html>"
    with respx.mock(assert_all_called=True) as router:
        router.get(_MIRROR).mock(return_value=httpx.Response(200, text=body))
        assert await _resolver().resolve(_TARGET) is None


@pytest.mark.asyncio
async def test_mirror_text_is_extracted_and_redirects_are_not_followed() -> None:
    body = "<html><body><p>Hello agents</p></body></html>"
    with respx.mock(assert_all_called=False) as router:
        mirror = router.get(_MIRROR).mock(return_value=httpx.Response(200, text=body))
        blocked = router.get("https://x.com/bob/status/99").mock(
            return_value=httpx.Response(200, text="should not be fetched")
        )
        assert await _resolver().resolve(_TARGET) == "Hello agents"
        assert mirror.call_count == 1
        assert blocked.call_count == 0


@pytest.mark.asyncio
async def test_redirect_is_not_followed() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(_MIRROR).mock(
            return_value=httpx.Response(
                302, headers={"location": "https://x.com/bob/status/99"}
            )
        )
        assert await _resolver().resolve(_TARGET) is None
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_bad_host_does_not_call_http() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.route().mock(side_effect=AssertionError("unexpected http"))
        assert await _resolver("https://mirror.example").resolve(_TARGET) is None
        assert await _resolver("").resolve(_TARGET) is None
        assert await _resolver("mirror.example/extra").resolve(_TARGET) is None
        assert router.calls.call_count == 0


@pytest.mark.asyncio
async def test_none_resolver_returns_nothing() -> None:
    assert await NoneResolver().resolve(_TARGET) is None
    assert mirror_url("mirror.example", _TARGET) == _MIRROR
