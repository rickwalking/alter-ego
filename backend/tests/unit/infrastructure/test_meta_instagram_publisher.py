"""Unit tests for MetaInstagramPublisher.

Gherkin: tests/features/instagram_publisher.feature
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
)


def _transport(handler: Any) -> httpx.AsyncClient:
    """Build an AsyncClient with a mock transport calling the handler."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _happy_path_handler() -> tuple[Any, dict[str, int]]:
    """Return (handler, counters) with successful responses for all steps."""
    counters: dict[str, int] = {
        "item_create": 0,
        "parent_create": 0,
        "status_poll": 0,
        "publish": 0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "media_publish" in request.url.path:
            counters["publish"] += 1
            return httpx.Response(200, json={"id": "post-final-123"})
        if request.method == "POST" and request.url.path.endswith("/media"):
            body = request.read().decode()
            if "is_carousel_item=true" in body:
                counters["item_create"] += 1
                return httpx.Response(
                    200, json={"id": f"item-{counters['item_create']}"}
                )
            counters["parent_create"] += 1
            return httpx.Response(200, json={"id": "parent-abc"})
        if request.method == "GET":
            counters["status_poll"] += 1
            return httpx.Response(200, json={"status_code": "FINISHED"})
        return httpx.Response(404)

    return handler, counters


@pytest.fixture(autouse=True)
def _fast_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop poll delay to zero so tests finish instantly."""
    monkeypatch.setattr(
        "rag_backend.infrastructure.external.meta_instagram_publisher._POLL_INTERVAL_SECONDS",
        0.0,
    )


@pytest.mark.unit
class TestMetaInstagramPublisherHappyPath:
    """Scenario: Happy path — 4 item containers, 1 parent, publish."""

    async def test_publishes_4_slide_carousel(self) -> None:
        handler, counters = _happy_path_handler()
        publisher = MetaInstagramPublisher(
            access_token="token",
            ig_user_id="ig-user",
            http_client=_transport(handler),
        )
        urls = [f"https://example.com/slide_{i}.jpg" for i in range(1, 5)]

        result = await publisher.publish_instagram("caption #tag", urls)

        assert result.status == "published"
        assert result.post_id == "post-final-123"
        assert counters["item_create"] == 4
        assert counters["parent_create"] == 1
        assert counters["publish"] == 1
        assert counters["status_poll"] >= 1


@pytest.mark.unit
class TestMetaInstagramPublisherConfiguration:
    """Scenarios: Missing token + image count validation."""

    async def test_missing_token_returns_failed_with_hint(self) -> None:
        publisher = MetaInstagramPublisher(access_token="", ig_user_id="")
        result = await publisher.publish_instagram(
            "caption",
            ["https://example.com/a.jpg", "https://example.com/b.jpg"],
        )
        assert result.status == "failed"
        assert "META_IG_ACCESS_TOKEN" in (result.error_message or "")

    async def test_fewer_than_two_images_rejected(self) -> None:
        publisher = MetaInstagramPublisher(access_token="t", ig_user_id="u")
        result = await publisher.publish_instagram(
            "caption", ["https://example.com/a.jpg"]
        )
        assert result.status == "failed"
        assert "at least 2" in (result.error_message or "")

    async def test_more_than_ten_images_rejected(self) -> None:
        publisher = MetaInstagramPublisher(access_token="t", ig_user_id="u")
        urls = [f"https://example.com/{i}.jpg" for i in range(11)]
        result = await publisher.publish_instagram("caption", urls)
        assert result.status == "failed"
        assert "at most 10" in (result.error_message or "")


@pytest.mark.unit
class TestMetaInstagramPublisherFailureModes:
    """Scenarios: ERROR status + HTTP 4xx passthrough."""

    async def test_container_error_status_fails_cleanly(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "media_publish" in request.url.path:
                return httpx.Response(200, json={"id": "should-not-reach"})
            if request.method == "POST":
                body = request.read().decode()
                if "is_carousel_item=true" in body:
                    return httpx.Response(200, json={"id": "item"})
                return httpx.Response(200, json={"id": "parent"})
            return httpx.Response(200, json={"status_code": "ERROR"})

        publisher = MetaInstagramPublisher(
            access_token="t",
            ig_user_id="u",
            http_client=_transport(handler),
        )
        urls = [f"https://example.com/{i}.jpg" for i in range(2)]
        result = await publisher.publish_instagram("cap", urls)
        assert result.status == "failed"
        assert "ERROR" in (result.error_message or "")

    async def test_http_400_surfaces_not_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": {"message": "bad request"}})

        publisher = MetaInstagramPublisher(
            access_token="t",
            ig_user_id="u",
            http_client=_transport(handler),
        )
        urls = [f"https://example.com/{i}.jpg" for i in range(2)]
        result = await publisher.publish_instagram("cap", urls)
        assert result.status == "failed"
        assert "Instagram API" in (result.error_message or "")
