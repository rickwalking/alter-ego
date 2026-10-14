"""Stepped and atomic Instagram gateways.

Gherkin: tests/features/autopilot_instagram_publish.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from rag_backend.domain.protocols.social import PublishResult
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.publish import CarouselMedia, StoredContainer
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import (
    AtomicInstagramGateway,
    SteppedInstagramGateway,
    gateway_for,
)
from tests.unit.infrastructure.test_meta_instagram_publisher import (
    _publisher,
    _transport,
)

_MEDIA = CarouselMedia(
    caption="caption",
    image_urls=("https://example.com/1.jpg", "https://example.com/2.jpg"),
)


def _ok(request: httpx.Request) -> httpx.Response:
    if "content_publishing_limit" in request.url.path:
        return httpx.Response(
            200, json={"data": [{"quota_usage": 0, "config": {"quota_total": 5}}]}
        )
    if "fields=permalink" in str(request.url):
        return httpx.Response(200, json={"permalink": "https://instagram.com/p/x"})
    if request.method == "GET":
        return httpx.Response(200, json={"status_code": "FINISHED"})
    return httpx.Response(200, json={"id": "media-1"})


@pytest.mark.unit
async def test_stepped_gateway_opens_finishes_and_reads_quota() -> None:
    publisher = _publisher("token", "ig-user", _transport(_ok))
    gateway = gateway_for(publisher)
    assert isinstance(gateway, SteppedInstagramGateway)
    assert gateway.can_resume() is True
    assert await gateway.current_token() == "token"
    assert gateway.user_configured() is True
    assert await gateway.quota_remaining() == 5
    container_id = await gateway.open_carousel(_MEDIA)
    post_id = await gateway.finish_container(
        StoredContainer(container_id=container_id, created_at=datetime.now(UTC))
    )
    assert post_id == "media-1"
    assert await gateway.permalink(post_id) == "https://instagram.com/p/x"
    atomic = await gateway.publish_atomic(_MEDIA)
    assert atomic.post_id == "media-1"


@pytest.mark.unit
async def test_atomic_gateway_forwards_and_refuses_steps() -> None:
    fake = AsyncMock()
    fake.publish_instagram = AsyncMock(
        return_value=PublishResult(status="published", post_id="atomic")
    )
    gateway = gateway_for(fake)
    assert isinstance(gateway, AtomicInstagramGateway)
    assert gateway.can_resume() is False
    assert await gateway.current_token() == ""
    assert gateway.user_configured() is False
    assert await gateway.quota_remaining() == 0
    outcome = await gateway.publish_atomic(_MEDIA)
    assert outcome.post_id == "atomic"
    with pytest.raises(InstagramCallError):
        await gateway.open_carousel(_MEDIA)
    with pytest.raises(InstagramCallError):
        await gateway.finish_container(
            StoredContainer(container_id="container", created_at=datetime.now(UTC))
        )
    with pytest.raises(InstagramCallError):
        await gateway.permalink("media")


@pytest.mark.unit
async def test_guard_translates_graph_runtime_and_transport_errors() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            raise httpx.ConnectError("down")
        raise RuntimeError("nope")

    publisher = _publisher("token", "ig-user", _transport(boom))
    gateway = SteppedInstagramGateway(publisher)
    with pytest.raises(InstagramCallError) as runtime_error:
        await gateway.open_carousel(_MEDIA)
    assert runtime_error.value.error_code == "nope"
    with pytest.raises(InstagramCallError) as transport_error:
        await gateway.quota_remaining()
    assert transport_error.value.transient is True

    def graph(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"code": 36003}})

    gateway = SteppedInstagramGateway(_publisher("token", "ig-user", _transport(graph)))
    with pytest.raises(InstagramCallError) as meta_error:
        await gateway.open_carousel(_MEDIA)
    assert meta_error.value.error_code == "36003"
    assert meta_error.value.transient is False
    assert InstagramGraphError is not InstagramCallError
