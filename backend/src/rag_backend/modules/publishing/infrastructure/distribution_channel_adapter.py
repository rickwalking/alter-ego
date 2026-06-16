"""Channel-delivery adapter for the publishing distribution port (AE-0129).

This adapter is the infrastructure backing for the publishing
:class:`~rag_backend.modules.publishing.domain.ports.DistributionPublisher`
port. It keeps the publishing APPLICATION/domain layers free of any vendor /
LLM SDK: the Meta Instagram vendor adapter (the
:class:`~rag_backend.domain.protocols.SocialPublisher` implementation) is
injected here and the vendor SDK imports stay in that adapter's module
(``infrastructure/external/meta_instagram_publisher.py``), never in the
publishing inner layers.

Behavior-preserving (AE-0129): ``publish_instagram`` forwards the EXACT caption +
public image URLs the route built to the vendor publisher and maps the vendor
``PublishResult`` one-to-one into the publishing
:class:`~rag_backend.modules.publishing.domain.models.DistributionResult` — the
``status`` / ``post_id`` / ``error_message`` values are untouched, so the
``publish/instagram`` response is byte-identical. ``caption_for`` projects the
already-persisted caption from the
:class:`~rag_backend.modules.publishing.domain.models.Publication` view (no LLM
call), identical to the legacy ``project.caption or ""`` route read. Mirrors the
presentation image-provider adapter pattern (AE-0119).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rag_backend.modules.publishing.domain.models import (
    DistributionResult,
    Publication,
)

if TYPE_CHECKING:
    from rag_backend.domain.protocols import SocialPublisher


class ChannelDistributionPublisher:
    """:class:`DistributionPublisher` backed by the Meta vendor + persisted copy.

    Wraps the injected social (Instagram) vendor adapter for channel delivery and
    projects the persisted caption for the distribution read. The vendor SDK lives
    in the wrapped adapter's module, so this seam — and the publishing inner layers
    behind it — stay SDK-free.
    """

    def __init__(self, social_publisher: SocialPublisher) -> None:
        self._social_publisher = social_publisher

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> DistributionResult:
        """Distribute the carousel slides to Instagram via the vendor adapter.

        Byte-identical to the legacy ``publisher.publish_instagram`` call: the same
        caption + image URLs are forwarded and the vendor result is mapped
        one-to-one into a :class:`DistributionResult`.
        """
        result = await self._social_publisher.publish_instagram(caption, image_urls)
        return DistributionResult(
            status=result.status,
            post_id=result.post_id,
            error_message=result.error_message,
        )

    @staticmethod
    def caption_for(publication: Publication) -> str:
        """Project the persisted social caption (empty string if unset)."""
        return publication.caption or ""


__all__ = ["ChannelDistributionPublisher"]
