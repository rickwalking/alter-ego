"""Unit tests for MetaInstagramPublisher.

Gherkin: tests/features/instagram_publisher.feature
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CONTAINER_FAILED,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
    GRAPH_HOST_FACEBOOK,
    GRAPH_HOST_INSTAGRAM,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_publisher_factory import (
    build_meta_instagram_publisher,
)
from rag_backend.infrastructure.external.instagram_token import (
    StaticInstagramTokenProvider,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
    MetaInstagramPublisherConfig,
)


def _publisher(
    token: str,
    user_id: str,
    client: httpx.AsyncClient | None = None,
    host: str = GRAPH_HOST_INSTAGRAM,
) -> MetaInstagramPublisher:
    """Build a publisher the way the container does, with an optional mock client."""
    return MetaInstagramPublisher(
        MetaInstagramPublisherConfig(
            ig_user_id=user_id,
            graph_base=host,
            token_provider=StaticInstagramTokenProvider(token),
        ),
        http_client=client,
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
        publisher = _publisher("token", "ig-user", _transport(handler))
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
        publisher = _publisher("", "")
        result = await publisher.publish_instagram(
            "caption",
            ["https://example.com/a.jpg", "https://example.com/b.jpg"],
        )
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED

    async def test_fewer_than_two_images_rejected(self) -> None:
        publisher = _publisher("t", "u")
        result = await publisher.publish_instagram(
            "caption", ["https://example.com/a.jpg"]
        )
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_IMAGE_COUNT_INVALID

    async def test_more_than_ten_images_rejected(self) -> None:
        publisher = _publisher("t", "u")
        urls = [f"https://example.com/{i}.jpg" for i in range(11)]
        result = await publisher.publish_instagram("caption", urls)
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_IMAGE_COUNT_INVALID


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

        publisher = _publisher("t", "u", _transport(handler))
        urls = [f"https://example.com/{i}.jpg" for i in range(2)]
        result = await publisher.publish_instagram("cap", urls)
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_CONTAINER_FAILED

    async def test_http_400_surfaces_not_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": {"message": "bad request"}})

        publisher = _publisher("t", "u", _transport(handler))
        urls = [f"https://example.com/{i}.jpg" for i in range(2)]
        result = await publisher.publish_instagram("cap", urls)
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_API_REQUEST_FAILED


@pytest.mark.unit
class TestInstagramLoginHost:
    """Scenario: Instagram Login token uses graph.instagram.com."""

    async def test_default_host_is_graph_instagram(self) -> None:
        import respx

        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.host)
            if (
                request.method == "GET"
                and "content_publishing_limit" in request.url.path
            ):
                return httpx.Response(
                    200,
                    json={"data": [{"quota_usage": 1, "config": {"quota_total": 25}}]},
                )
            if request.method == "GET" and "fields=permalink" in str(request.url):
                return httpx.Response(
                    200, json={"permalink": "https://instagram.com/p/x"}
                )
            if request.method == "GET":
                return httpx.Response(200, json={"status_code": "FINISHED"})
            return httpx.Response(200, json={"id": "media-1"})

        with respx.mock(assert_all_called=False) as router:
            router.route(host="graph.instagram.com").mock(side_effect=handler)
            publisher = _publisher("IGAA-token", "ig-user")
            urls = [f"https://example.com/{i}.jpg" for i in range(2)]
            result = await publisher.publish_instagram("caption", urls)
            remaining = await publisher.content_publishing_remaining()
            link = await publisher.fetch_permalink("media-1")

        assert result.status == "published"
        assert remaining == 24
        assert link == "https://instagram.com/p/x"
        assert seen
        assert set(seen) == {"graph.instagram.com"}

    async def test_facebook_host_stays_selectable(self) -> None:
        import respx

        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.host)
            return httpx.Response(200, json={"id": "item-1"})

        with respx.mock(assert_all_called=False) as router:
            router.route(host="graph.facebook.com").mock(side_effect=handler)
            publisher = _publisher("page-token", "ig-user", host=GRAPH_HOST_FACEBOOK)
            await publisher.create_carousel_container(
                "caption",
                ["https://example.com/1.jpg", "https://example.com/2.jpg"],
            )

        assert seen
        assert set(seen) == {"graph.facebook.com"}

    def test_settings_default_host(self) -> None:
        assert (
            Settings.model_fields["meta_ig_graph_base"].default == GRAPH_HOST_INSTAGRAM
        )

    async def test_factory_reads_the_configured_host(self) -> None:
        import respx

        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.host)
            return httpx.Response(200, json={"id": "item-1"})

        settings = Settings(
            meta_ig_graph_base=GRAPH_HOST_FACEBOOK,
            meta_ig_user_id="ig-user",
            meta_ig_access_token="page-token",
        )
        with respx.mock(assert_all_called=False) as router:
            router.route(host="graph.facebook.com").mock(side_effect=handler)
            publisher = build_meta_instagram_publisher(settings)
            await publisher.create_carousel_container(
                "caption",
                ["https://example.com/1.jpg", "https://example.com/2.jpg"],
            )

        assert set(seen) == {"graph.facebook.com"}


@pytest.mark.unit
class TestPublisherEdgeBranches:
    """Timeout, transport failure, unreadable quota, and a missing media id."""

    async def test_poll_timeout_is_a_failed_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "rag_backend.infrastructure.external.meta_instagram_publisher.META_POLL_MAX_ATTEMPTS",
            1,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(200, json={"id": "parent"})
            return httpx.Response(200, json={"status_code": "IN_PROGRESS"})

        publisher = _publisher("t", "u", _transport(handler))
        result = await publisher.publish_instagram(
            "cap", ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        )
        assert result.error_message == "instagram_container_timeout"

    async def test_transport_error_is_a_failed_result(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        publisher = _publisher("t", "u", _transport(handler))
        result = await publisher.publish_instagram(
            "cap", ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        )
        assert result.status == "failed"
        assert result.error_message == ERR_INSTAGRAM_API_REQUEST_FAILED

    async def test_missing_media_id_fails(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        publisher = _publisher("t", "u", _transport(handler))
        result = await publisher.publish_instagram(
            "cap", ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        )
        assert result.error_message == "instagram_api_no_id"

    async def test_unreadable_quota_and_blank_permalink(self) -> None:
        from rag_backend.infrastructure.external.instagram_graph_error import (
            InstagramGraphError,
        )

        quota = _publisher(
            "t",
            "u",
            _transport(
                lambda _request: httpx.Response(
                    200, json={"data": [{"quota_usage": True}]}
                )
            ),
        )
        with pytest.raises(InstagramGraphError):
            await quota.content_publishing_remaining()
        permalink = _publisher(
            "t",
            "u",
            _transport(lambda _request: httpx.Response(200, json={"permalink": ""})),
        )
        with pytest.raises(InstagramGraphError):
            await permalink.fetch_permalink("media-1")
        await permalink.close()
