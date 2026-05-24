"""In-memory event publisher for tests and dev without Redis."""

from __future__ import annotations

import uuid

from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_MEMORY_EVENTS: list[tuple[str, dict[str, object], str]] = []


class MemoryEventPublisher:
    """Stores events in process memory (test/dev fallback)."""

    async def publish(self, stream: str, event: dict[str, object]) -> str:
        entry_id = str(uuid.uuid4())
        _MEMORY_EVENTS.append((stream, event, entry_id))
        logger.info(
            "event_published_memory",
            stream=stream,
            event_type=event.get("event_type"),
        )
        return entry_id

    async def close(self) -> None:
        return None


def get_memory_events() -> list[tuple[str, dict[str, object], str]]:
    """Return captured events (test helper)."""
    return list(_MEMORY_EVENTS)


def clear_memory_events() -> None:
    """Clear captured events (test helper)."""
    _MEMORY_EVENTS.clear()


__all__ = ["MemoryEventPublisher", "clear_memory_events", "get_memory_events"]
