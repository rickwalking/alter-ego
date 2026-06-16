"""Unit tests for the publishing distribution port + channel adapter (AE-0129).

These tests prove the behavior-preserving extraction of channel delivery
(captions / Instagram / LinkedIn) behind the publishing
:class:`~rag_backend.modules.publishing.domain.ports.DistributionPublisher`
port + the channel adapter:

* the channel adapter forwards the EXACT caption + image-url payload to the
  wrapped vendor publisher and maps its result one-to-one (byte-identical
  channel payload + response shape, deterministic stub — no live Meta key);
* the adapter projects the persisted caption / LinkedIn copy from the
  :class:`Publication` view (no LLM call), identical to the legacy reads;
* the application service routes ``publish_instagram`` / ``read_caption`` /
  ``read_linkedin_posts`` through the distribution port;
* ``bootstrap_module`` wires the distribution publisher into the service;
* the service raises a clear error when the distribution port is unwired.

Behavior-preserving extraction; the live-response diff is asserted by the AE-0125
safety net (Gherkin not applicable — see ticket AE-0129).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import PublishResult, SocialPublisher
from rag_backend.modules.publishing import (
    CarouselRepository,
    ChannelDistributionPublisher,
    DistributionResult,
    Publication,
    PublishingAdapters,
    PublishingPorts,
    PublishingService,
    bootstrap_module,
)

# Deterministic channel fixtures (no live Meta/LLM key is ever used).
_CAPTION = "Deterministic caption"
_IMAGE_URLS = ["https://example.test/1.jpg", "https://example.test/2.jpg"]
_POST_ID = "IG_TEST_POST_ID"
_LINKEDIN_PT = "Post em portugues"
_LINKEDIN_EN = "Post in English"


def _make_publication(
    *,
    caption: str | None = None,
    linkedin_pt: str | None = None,
    linkedin_en: str | None = None,
) -> Publication:
    """Build a publication view over a carousel with the given distribution copy."""
    project = CarouselProject(
        topic="AI",
        audience="devs",
        niche="tech",
        caption=caption,
        linkedin_post_pt=linkedin_pt,
        linkedin_post_en=linkedin_en,
    )
    return Publication(project=project)


class _StubSocialPublisher:
    """Deterministic in-memory SocialPublisher (never calls Meta/Instagram)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    async def publish_instagram(
        self, caption: str, image_urls: list[str]
    ) -> PublishResult:
        self.calls.append((caption, list(image_urls)))
        return PublishResult(status="published", post_id=_POST_ID)


class TestChannelDistributionAdapter:
    """Scenario: the channel adapter forwards to the vendor + maps the result."""

    @pytest.mark.asyncio
    async def test_publish_instagram_forwards_exact_payload(self) -> None:
        stub = _StubSocialPublisher()
        adapter = ChannelDistributionPublisher(stub)

        result = await adapter.publish_instagram(_CAPTION, _IMAGE_URLS)

        # The vendor adapter received the EXACT caption + image URLs (unchanged).
        assert stub.calls == [(_CAPTION, _IMAGE_URLS)]
        # The vendor result is mapped one-to-one into a DistributionResult.
        assert result == DistributionResult(status="published", post_id=_POST_ID)

    @pytest.mark.asyncio
    async def test_publish_instagram_maps_failed_result(self) -> None:
        failing = AsyncMock(spec=SocialPublisher)
        failing.publish_instagram.return_value = PublishResult(
            status="failed", error_message="boom"
        )
        adapter = ChannelDistributionPublisher(failing)

        result = await adapter.publish_instagram(_CAPTION, _IMAGE_URLS)

        assert result == DistributionResult(status="failed", error_message="boom")

    def test_caption_for_projects_persisted_caption(self) -> None:
        adapter = ChannelDistributionPublisher(_StubSocialPublisher())
        publication = _make_publication(caption=_CAPTION)

        assert adapter.caption_for(publication) == _CAPTION

    def test_caption_for_returns_empty_string_when_unset(self) -> None:
        adapter = ChannelDistributionPublisher(_StubSocialPublisher())
        publication = _make_publication(caption=None)

        assert adapter.caption_for(publication) == ""

    def test_linkedin_posts_for_projects_persisted_copy(self) -> None:
        adapter = ChannelDistributionPublisher(_StubSocialPublisher())
        publication = _make_publication(
            linkedin_pt=_LINKEDIN_PT, linkedin_en=_LINKEDIN_EN
        )

        assert adapter.linkedin_posts_for(publication) == (_LINKEDIN_PT, _LINKEDIN_EN)


class TestDistributionService:
    """Scenario: the service routes distribution through the port."""

    @pytest.mark.asyncio
    async def test_publish_instagram_routes_to_port(self) -> None:
        stub = _StubSocialPublisher()
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(
                distribution=ChannelDistributionPublisher(stub)
            ),
        )

        result = await service.publish_instagram(_CAPTION, _IMAGE_URLS)

        assert stub.calls == [(_CAPTION, _IMAGE_URLS)]
        assert result == DistributionResult(status="published", post_id=_POST_ID)

    @pytest.mark.asyncio
    async def test_read_caption_routes_to_port(self) -> None:
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(
                distribution=ChannelDistributionPublisher(_StubSocialPublisher())
            ),
        )

        caption = await service.read_caption(_make_publication(caption=_CAPTION))

        assert caption == _CAPTION

    @pytest.mark.asyncio
    async def test_read_linkedin_posts_routes_to_port(self) -> None:
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(
                distribution=ChannelDistributionPublisher(_StubSocialPublisher())
            ),
        )

        posts = await service.read_linkedin_posts(
            _make_publication(linkedin_pt=_LINKEDIN_PT, linkedin_en=_LINKEDIN_EN)
        )

        assert posts == (_LINKEDIN_PT, _LINKEDIN_EN)

    @pytest.mark.asyncio
    async def test_publish_instagram_without_port_raises(self) -> None:
        service = PublishingService(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            ports=PublishingPorts(),
        )

        with pytest.raises(RuntimeError):
            await service.publish_instagram(_CAPTION, _IMAGE_URLS)


class TestBootstrapWiresDistribution:
    """Scenario: bootstrap_module wires the distribution publisher in."""

    @pytest.mark.asyncio
    async def test_bootstrap_wires_distribution_publisher(self) -> None:
        stub = _StubSocialPublisher()
        adapters = PublishingAdapters(
            carousel_repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
            distribution_publisher=ChannelDistributionPublisher(stub),
        )

        module = bootstrap_module(platform=object(), adapters=adapters)
        result = await module.service.publish_instagram(_CAPTION, _IMAGE_URLS)

        assert stub.calls == [(_CAPTION, _IMAGE_URLS)]
        assert result == DistributionResult(status="published", post_id=_POST_ID)
