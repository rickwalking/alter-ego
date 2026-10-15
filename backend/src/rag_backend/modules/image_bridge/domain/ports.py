"""Outbound ports of the image bridge module (AE-0393).

Infrastructure implements these; the application services depend only on
the Protocols, wired by ``bootstrap``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.image_bridge.domain.models import (
    ImageBridgeJob,
    JobDeadline,
    JobFailure,
    JobSuccess,
    WebhookRequest,
)


class ImageBridgeJobRepository(Protocol):
    """Durable job store shared by every worker (Postgres in prod).

    Every transition is conditional on the job still being ``pending``; it
    returns ``False`` when another writer got there first.
    """

    async def create(self, job: ImageBridgeJob) -> None:
        """Insert a new pending job."""
        ...

    async def get(self, job_id: UUID) -> ImageBridgeJob | None:
        """The job, or ``None`` when it does not exist."""
        ...

    async def succeed(self, success: JobSuccess) -> bool:
        """Store the image and mark the job succeeded, if still in time."""
        ...

    async def fail(self, failure: JobFailure) -> bool:
        """Mark a pending job failed with a code and message."""
        ...

    async def expire(self, deadline: JobDeadline) -> bool:
        """Mark a pending job expired."""
        ...

    async def take_image(self, job_id: UUID) -> bytes | None:
        """Read the stored image once and null it."""
        ...

    async def sweep(self, now: datetime) -> None:
        """Expire overdue pending jobs and delete rows past retention."""
        ...


class GrokBotWebhook(Protocol):
    """Sends one job to the Grok Bot. Raises ``WebhookDeliveryError``."""

    async def deliver(self, request: WebhookRequest) -> None:
        """POST the job; any non-2xx answer or transport error raises."""
        ...


class BridgeClock(Protocol):
    """Time source for deadlines and the poll interval."""

    def now(self) -> datetime:
        """Current time, timezone-aware UTC."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Wait between polls."""
        ...


@dataclass(frozen=True)
class NormalizeRequest:
    """Resize ``image`` to exactly ``width`` x ``height``."""

    image: bytes
    width: int
    height: int


class ImageCodec(Protocol):
    """Image decoding and normalization (Pillow in prod). CPU-bound, sync."""

    def validate(self, image: bytes) -> None:
        """Raise ``InvalidCallbackImageError`` unless the image is acceptable."""
        ...

    def normalize(self, request: NormalizeRequest) -> bytes:
        """The image fitted to the requested size, encoded as PNG."""
        ...
