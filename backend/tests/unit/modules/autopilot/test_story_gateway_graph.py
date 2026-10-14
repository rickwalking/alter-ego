"""Story Graph calls with the real Graph shapes (AE-0369).

Gherkin: tests/features/autopilot_story_and_music.feature
  Scenario: The Story is created, polled, and published through Graph
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from rag_backend.domain.constants.instagram_publish import GRAPH_HOST_INSTAGRAM
from rag_backend.domain.protocols.social import PublishResult
from rag_backend.infrastructure.external import meta_instagram_publisher
from rag_backend.infrastructure.external.instagram_token import (
    StaticInstagramTokenProvider,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.publish import StoredContainer
from rag_backend.modules.autopilot.infrastructure.story_gateway import (
    SteppedStoryGateway,
    story_gateway_for,
)

_BASE = GRAPH_HOST_INSTAGRAM
_USER = "ig-user"
_IMAGE = "https://api.test/api/carousels/p-1/story-image/pt.jpg"
_CONTAINER = StoredContainer(
    container_id="story-c-1", created_at=datetime(2026, 10, 14, tzinfo=UTC)
)


def _publisher() -> MetaInstagramPublisher:
    return MetaInstagramPublisher(
        MetaInstagramPublisherConfig(
            ig_user_id=_USER,
            graph_base=_BASE,
            token_provider=StaticInstagramTokenProvider("IGAA-token"),
        )
    )


def _form(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode())


@pytest.fixture(autouse=True)
def _no_poll_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meta_instagram_publisher, "_POLL_INTERVAL_SECONDS", 0)


@pytest.mark.unit
class TestStoryGraphCalls:
    """STORIES container, status_code polls with ``fields``, then media_publish."""

    async def test_create_poll_and_publish(self) -> None:
        statuses = iter(["IN_PROGRESS", "FINISHED"])
        with respx.mock(assert_all_called=True) as router:
            create = router.post(f"{_BASE}/{_USER}/media").respond(
                200, json={"id": "story-c-1"}
            )
            poll = router.get(
                f"{_BASE}/story-c-1", params={"fields": "status_code"}
            ).mock(
                side_effect=lambda _r: httpx.Response(
                    200, json={"status_code": next(statuses), "id": "story-c-1"}
                )
            )
            publish = router.post(f"{_BASE}/{_USER}/media_publish").respond(
                200, json={"id": "story-m-1"}
            )
            gateway = SteppedStoryGateway(_publisher())

            container_id = await gateway.open_story(_IMAGE)
            media_id = await gateway.finish_story(
                StoredContainer(
                    container_id=container_id, created_at=_CONTAINER.created_at
                )
            )

        assert media_id == "story-m-1"
        body = _form(create.calls.last.request)
        assert body["media_type"] == ["STORIES"]
        assert body["image_url"] == [_IMAGE]
        assert "is_carousel_item" not in body
        assert poll.call_count == 2
        assert _form(publish.calls.last.request)["creation_id"] == ["story-c-1"]

    async def test_already_published_container_is_not_published_again(self) -> None:
        with respx.mock(assert_all_called=False) as router:
            router.get(f"{_BASE}/story-c-1").respond(
                200, json={"status_code": "PUBLISHED"}
            )
            publish = router.post(f"{_BASE}/{_USER}/media_publish").respond(
                200, json={"id": "never"}
            )
            gateway = SteppedStoryGateway(_publisher())

            assert await gateway.finish_story(_CONTAINER) is None
            assert await gateway.was_published(_CONTAINER) is True

        assert publish.call_count == 0

    async def test_finished_container_was_not_published(self) -> None:
        with respx.mock() as router:
            router.get(f"{_BASE}/story-c-1", params={"fields": "status_code"}).respond(
                200, json={"status_code": "FINISHED"}
            )
            assert (
                await SteppedStoryGateway(_publisher()).was_published(_CONTAINER)
                is False
            )

    async def test_meta_error_becomes_a_permanent_call_error(self) -> None:
        with respx.mock() as router:
            router.post(f"{_BASE}/{_USER}/media").respond(
                400, json={"error": {"code": 36003, "message": "bad ratio"}}
            )
            with pytest.raises(InstagramCallError) as caught:
                await SteppedStoryGateway(_publisher()).open_story(_IMAGE)

        assert caught.value.error_code == "36003"
        assert caught.value.transient is False

    async def test_quota_read_asks_for_config_and_usage(self) -> None:
        with respx.mock() as router:
            limit = router.get(
                f"{_BASE}/{_USER}/content_publishing_limit",
                params={"fields": "config,quota_usage"},
            ).respond(
                200,
                json={"data": [{"quota_usage": 2, "config": {"quota_total": 25}}]},
            )
            assert await _publisher().content_publishing_remaining() == 23

        assert limit.call_count == 1


@pytest.mark.unit
class TestStoryGatewayFor:
    """Scenario: A publisher that cannot post Stories skips the Story step."""

    def test_graph_publisher_gets_a_story_gateway(self) -> None:
        assert isinstance(story_gateway_for(_publisher()), SteppedStoryGateway)

    def test_other_publishers_get_none(self) -> None:
        class _Stub:
            async def publish_instagram(
                self, caption: str, image_urls: list[str]
            ) -> PublishResult:
                del caption, image_urls
                return PublishResult(status="published", post_id="p-1")

        assert story_gateway_for(_Stub()) is None
