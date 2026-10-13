"""Adapt ``SocialPublisher`` / ``MetaInstagramPublisher`` to the publish-job port.

A real Graph publisher can pause after the container id is stored. A test
double that only implements ``publish_instagram`` stays one-shot, which is
how the existing manual-route tests keep working.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_REQUEST_FAILED,
)
from rag_backend.domain.protocols.social import SocialPublisher
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisher,
)
from rag_backend.modules.autopilot.constants import REASON_CONTAINER_MISSING
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
)

_T = TypeVar("_T")


class SteppedInstagramGateway:
    """Graph steps backed by ``MetaInstagramPublisher``."""

    def __init__(self, publisher: MetaInstagramPublisher) -> None:
        self._publisher = publisher
        self._resumable = True

    def can_resume(self) -> bool:
        """Container creation and ``media_publish`` are separate calls."""
        return self._resumable

    async def current_token(self) -> str:
        """Token from the publisher's provider."""
        return await self._publisher.current_token()

    def user_configured(self) -> bool:
        """True when the Instagram user id is set."""
        return self._publisher.user_configured()

    async def quota_remaining(self) -> int:
        """Remaining ``content_publishing_limit`` quota."""
        return await _guard(self._publisher.content_publishing_remaining)

    async def open_carousel(self, media: CarouselMedia) -> str:
        """Create the parent container."""
        return await _guard(
            lambda: self._publisher.create_carousel_container(
                media.caption, list(media.image_urls)
            )
        )

    async def finish_container(self, container_id: str) -> str:
        """Poll, then ``media_publish``."""
        await _guard(lambda: self._publisher.await_container(container_id))
        return await _guard(lambda: self._publisher.media_publish(container_id))

    async def permalink(self, media_id: str) -> str:
        """Public URL for the published media."""
        return await _guard(lambda: self._publisher.fetch_permalink(media_id))

    async def publish_atomic(self, media: CarouselMedia) -> AtomicPublishResult:
        """Full publish for a carousel that has no autopilot run to checkpoint."""
        result = await self._publisher.publish_instagram(
            media.caption, list(media.image_urls)
        )
        return AtomicPublishResult(
            status=result.status,
            post_id=result.post_id,
            error_message=result.error_message,
        )


class AtomicInstagramGateway:
    """One-shot adapter for publishers that only implement ``publish_instagram``."""

    def __init__(self, publisher: SocialPublisher) -> None:
        self._publisher = publisher
        self._resumable = False
        self._token = ""
        self._quota = 0

    def can_resume(self) -> bool:
        """There is no container id to resume."""
        return self._resumable

    async def current_token(self) -> str:
        """Unused on the atomic path."""
        return self._token

    def user_configured(self) -> bool:
        """Unused on the atomic path."""
        return self._resumable

    async def quota_remaining(self) -> int:
        """Unused on the atomic path."""
        return self._quota

    async def open_carousel(self, media: CarouselMedia) -> str:
        """Atomic publishers cannot open a container separately."""
        del media
        raise self._unsupported()

    async def finish_container(self, container_id: str) -> str:
        """Atomic publishers cannot publish a stored container."""
        del container_id
        raise self._unsupported()

    async def permalink(self, media_id: str) -> str:
        """Atomic publishers do not fetch a permalink."""
        del media_id
        raise self._unsupported()

    def _unsupported(self) -> InstagramCallError:
        if self._resumable:
            return _atomic_unsupported()
        return _atomic_unsupported()

    async def publish_atomic(self, media: CarouselMedia) -> AtomicPublishResult:
        """Forward the caption and slide URLs unchanged."""
        result = await self._publisher.publish_instagram(
            media.caption, list(media.image_urls)
        )
        return AtomicPublishResult(
            status=result.status,
            post_id=result.post_id,
            error_message=result.error_message,
        )


def _atomic_unsupported() -> InstagramCallError:
    return InstagramCallError(
        status_code=0,
        error_code=REASON_CONTAINER_MISSING,
        transient=False,
    )


def gateway_for(
    publisher: SocialPublisher,
) -> SteppedInstagramGateway | AtomicInstagramGateway:
    """Pick the stepped gateway only for the real Graph publisher."""
    if isinstance(publisher, MetaInstagramPublisher):
        return SteppedInstagramGateway(publisher)
    return AtomicInstagramGateway(publisher)


async def _guard(call: Callable[[], Awaitable[_T]]) -> _T:
    try:
        return await call()
    except (InstagramGraphError, RuntimeError, httpx.HTTPError) as exc:
        raise _translate(exc) from exc


def _translate(
    exc: InstagramGraphError | RuntimeError | httpx.HTTPError,
) -> InstagramCallError:
    if isinstance(exc, InstagramGraphError):
        return InstagramCallError(
            status_code=exc.status_code,
            error_code=exc.error_code,
            transient=exc.transient,
        )
    if isinstance(exc, httpx.HTTPError):
        return InstagramCallError(
            status_code=0,
            error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
            transient=True,
        )
    return InstagramCallError(status_code=0, error_code=str(exc), transient=False)
