"""Protocol for publishing workflow domain events."""

from __future__ import annotations

from typing import Protocol


class EventPublisherProtocol(Protocol):
    """Publishes domain events to the event backbone."""

    async def publish(self, stream: str, event: dict[str, object]) -> str:
        """Publish an event and return the stream entry id."""

    async def close(self) -> None:
        """Release publisher resources."""


__all__ = ["EventPublisherProtocol"]
