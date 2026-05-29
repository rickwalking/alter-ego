"""In-process SSE fan-out for editorial carousel workflow events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from rag_backend.application.services.carousel.editorial_workflow_support import (
    SSE_EVENT_KEEPALIVE,
    WORKFLOW_SSE_KEEPALIVE_SECONDS,
    WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT,
)


class WorkflowSseSubscriberLimitError(Exception):
    """Raised when a project exceeds the allowed SSE subscriber count."""


class WorkflowSseHub:
    """Broadcast workflow SSE payloads to active stream subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, object] | None]]] = (
            defaultdict(set)
        )
        self._lock = asyncio.Lock()

    def subscriber_count(self, project_id: str) -> int:
        """Return the number of active subscribers for a project."""
        return len(self._subscribers.get(project_id, set()))

    def can_accept_subscriber(self, project_id: str) -> bool:
        """Return whether another SSE subscriber may connect."""
        return (
            self.subscriber_count(project_id) < WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT
        )

    async def publish(self, project_id: str, event: dict[str, object]) -> None:
        """Push an event to all subscribers for the project."""
        async with self._lock:
            queues = list(self._subscribers.get(project_id, set()))
        for queue in queues:
            await queue.put(event)

    async def listen(
        self,
        project_id: str,
        *,
        keepalive_seconds: float = WORKFLOW_SSE_KEEPALIVE_SECONDS,
    ) -> AsyncIterator[dict[str, object]]:
        """Yield published events; emit keepalive markers on idle timeouts."""
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
        async with self._lock:
            if not self.can_accept_subscriber(project_id):
                raise WorkflowSseSubscriberLimitError(project_id)
            self._subscribers[project_id].add(queue)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=keepalive_seconds
                    )
                except TimeoutError:
                    yield {SSE_EVENT_KEY: SSE_EVENT_KEEPALIVE}
                    continue
                if event is None:
                    break
                yield event
        finally:
            async with self._lock:
                self._subscribers[project_id].discard(queue)
                if not self._subscribers[project_id]:
                    del self._subscribers[project_id]


SSE_EVENT_KEY = "event"

_hub: WorkflowSseHub | None = None


def get_workflow_sse_hub() -> WorkflowSseHub:
    """Return the process-wide workflow SSE hub singleton."""
    global _hub
    if _hub is None:
        _hub = WorkflowSseHub()
    return _hub


def reset_workflow_sse_hub() -> None:
    """Reset the process-wide hub singleton (test isolation)."""
    global _hub
    _hub = None


__all__ = [
    "SSE_EVENT_KEY",
    "WorkflowSseHub",
    "WorkflowSseSubscriberLimitError",
    "get_workflow_sse_hub",
    "reset_workflow_sse_hub",
]
