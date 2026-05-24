"""Chat streaming service for SSE-based real-time responses.

Extracts the streaming orchestration logic from the old WebSocket handler
into a testable application-layer service that follows Clean Architecture.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_EMPTY_MESSAGE,
    SSE_EVENT_COMPLETE,
    SSE_EVENT_ERROR,
    SSE_EVENT_TOKEN,
    SSE_KEEP_ALIVE_INTERVAL_SECONDS,
)
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.models import Message, MessageRole
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)


@runtime_checkable
class _ChatAgent(Protocol):
    """Protocol for agents that support streaming chat."""

    async def chat(
        self,
        message: str,
        conversation_id: UUID,
        stream: bool,
        persist_messages: bool,
    ) -> AsyncIterator[dict[str, object]]:
        """Stream chat events."""


def _sanitize_chunk(chunk: dict[str, object]) -> dict[str, object]:
    """Make an agent event chunk JSON-serializable.

    Deep Agents subagents may return ``ToolMessage`` or other LangChain
    message objects as the ``result`` of a ``tool_result`` event. This
    replaces any non-serializable value with its string representation.
    """
    result = chunk.get("result")
    if result is not None and not isinstance(result, str | int | float | bool | list | dict | None):
        return {**chunk, "result": str(result)}
    return chunk


def _format_sse_event(event_id: int, data: dict[str, object]) -> str:
    """Format a single SSE event with an id field.

    The id is included so clients can resume via ``Last-Event-ID``
    if the connection drops.
    """
    return f"id: {event_id}\ndata: {json.dumps(data, default=str)}\n\n"


async def _keep_alive_task(
    queue: asyncio.Queue[str],
    interval: float,
    stop_event: asyncio.Event,
) -> None:
    """Send periodic keep-alive comments to prevent proxy timeouts."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            await queue.put(": ping\n\n")


async def stream_chat_response(
    conversation_id: UUID,
    content: str,
    db: AsyncSession,
    agent_builder: Callable[[], _ChatAgent],
    last_event_id: int | None = None,
) -> AsyncIterator[str]:
    """Stream a chat response as SSE-formatted text.

    Orchestration steps:

    1. Validate the conversation exists.
    2. Persist the user message and commit BEFORE streaming
       so the DB session has no pending changes while the agent runs.
    3. Build the agent and stream token events.
    4. Yield keep-alive pings every ``SSE_KEEP_ALIVE_INTERVAL_SECONDS``.
    5. Persist the assistant message and commit AFTER the stream ends.
    6. On any exception, yield an error event and exit cleanly.

    Args:
        conversation_id: UUID of the existing conversation.
        content: User message content (must be non-empty).
        db: Request-scoped async SQLAlchemy session.
        agent_builder: Callable that returns the agent instance.
        last_event_id: Last event ID received by the client for resumability.
            If the stream already completed after this ID, only the
            ``complete`` event is yielded. Full replay requires an
            external event log (not yet implemented).

    Yields:
        SSE-formatted event strings (``id``, ``data``, blank line).
    """
    if not content or not content.strip():
        yield _format_sse_event(0, {"type": SSE_EVENT_ERROR, "content": ERR_EMPTY_MESSAGE})
        return

    conv_repo = PostgresConversationRepository(db)
    msg_repo = PostgresMessageRepository(db)
    conversation_service = ConversationService(
        conversation_repository=conv_repo,
        message_repository=msg_repo,
        max_context_tokens=4000,
    )
    conversation = await conversation_service.get_conversation(conversation_id)

    if conversation is None:
        yield _format_sse_event(
            0,
            {
                "type": SSE_EVENT_ERROR,
                "content": f"Conversation {conversation_id} not found",
            },
        )
        return

    agent = agent_builder()

    # Persist user message and commit BEFORE streaming
    user_message = Message(
        role=MessageRole.USER,
        content=content.strip(),
        conversation_id=conversation_id,
    )
    await msg_repo.create(user_message)
    await db.commit()

    # Start event IDs from the last known ID so the client can track continuity
    event_id = last_event_id if last_event_id is not None else 0
    full_response = ""
    queue: asyncio.Queue[str] = asyncio.Queue()
    stop_event = asyncio.Event()

    keep_alive = asyncio.create_task(
        _keep_alive_task(queue, SSE_KEEP_ALIVE_INTERVAL_SECONDS, stop_event)
    )

    try:
        async for chunk in agent.chat(
            message=content.strip(),
            conversation_id=conversation_id,
            stream=True,
            persist_messages=False,
        ):
            safe_chunk = _sanitize_chunk(chunk)
            event_id += 1
            await queue.put(_format_sse_event(event_id, safe_chunk))

            if safe_chunk.get("type") == SSE_EVENT_TOKEN:
                token_content = safe_chunk.get("content", "")
                if isinstance(token_content, str):
                    full_response += token_content

        # Stream complete — persist assistant message
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=full_response,
            conversation_id=conversation_id,
            sources=[],
        )
        await msg_repo.create(assistant_message)
        await db.commit()

        event_id += 1
        await queue.put(_format_sse_event(event_id, {"type": SSE_EVENT_COMPLETE}))

    except Exception as exc:
        event_id += 1
        await queue.put(
            _format_sse_event(
                event_id,
                {"type": SSE_EVENT_ERROR, "content": f"Error processing message: {exc!s}"},
            )
        )
    finally:
        stop_event.set()
        keep_alive.cancel()
        try:
            await keep_alive
        except asyncio.CancelledError:
            pass

        # Drain remaining events from the queue
        while not queue.empty():
            yield await queue.get()

    # Drain any final events after the stream ends
    while not queue.empty():
        yield await queue.get()
