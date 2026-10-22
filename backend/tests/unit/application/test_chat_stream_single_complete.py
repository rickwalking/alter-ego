"""The chat stream ends with exactly one ``complete`` event.

Feature file: tests/features/alter_ego_chat_sse.feature
"""

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from rag_backend.application.services.chat_stream_service import (
    _ChatContext,
    _run_stream,
    _StreamState,
)
from rag_backend.domain.constants.chat_stream import (
    SSE_EVENT_COMPLETE,
    SSE_EVENT_TOKEN,
)


class _AgentEndingWithComplete:
    """An agent that, like the real ones, ends its stream with ``complete``."""

    async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
        del ctx
        yield {"type": SSE_EVENT_TOKEN, "content": "O"}
        yield {"type": SSE_EVENT_TOKEN, "content": "K"}
        yield {"type": SSE_EVENT_COMPLETE, "content": "OK"}


def _queued_types(queue: asyncio.Queue[str]) -> list[str]:
    types: list[str] = []
    while not queue.empty():
        frame = queue.get_nowait()
        data = next(line for line in frame.splitlines() if line.startswith("data: "))
        types.append(json.loads(data[len("data: ") :])["type"])
    return types


@pytest.mark.asyncio
async def test_agent_complete_is_not_forwarded() -> None:
    """The agent's own ``complete`` is dropped; the service sends the one after saving."""
    # Scenario: The stream ends with a single complete event
    queue: asyncio.Queue[str] = asyncio.Queue()
    state = _StreamState(uuid4())

    event_id, full_response = await _run_stream(
        (_AgentEndingWithComplete, "Say OK"), state, queue
    )

    assert _queued_types(queue) == [SSE_EVENT_TOKEN, SSE_EVENT_TOKEN]
    assert full_response == "OK"
    assert event_id == 2
