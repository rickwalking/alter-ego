from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publishing call."""

    status: str  # "queued" | "published" | "failed"
    post_id: str | None = None
    error_message: str | None = None


class SocialPublisher(Protocol):
    """Protocol for publishing a carousel to a social network.

    Implementations translate project content + media into whatever the
    vendor SDK needs. The agent pipeline talks only to this interface,
    so swapping Meta Graph API for a broker (Publer, Ayrshare) later is
    a one-class change.
    """

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> PublishResult: ...
