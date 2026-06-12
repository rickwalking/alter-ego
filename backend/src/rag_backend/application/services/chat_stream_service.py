"""Chat streaming service for SSE-based real-time responses.

Extracts the streaming orchestration logic from the old WebSocket handler
into a testable application-layer service that follows Clean Architecture.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.constants.chat_stream import (
    ERR_EMPTY_MESSAGE,
    SSE_EVENT_COMPLETE,
    SSE_EVENT_ERROR,
    SSE_EVENT_TOKEN,
    SSE_KEEP_ALIVE_INTERVAL_SECONDS,
)
from rag_backend.domain.models import Message, MessageRole
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)


@dataclass(frozen=True)
class _ChatContext:
    """Parameters for a single streaming chat invocation."""

    message: str
    conversation_id: UUID
    stream: bool = True
    persist_messages: bool = True


@runtime_checkable
class _ChatAgent(Protocol):
    """Protocol for agents that support streaming chat."""

    async def chat(
        self,
        ctx: _ChatContext,
    ) -> AsyncIterator[dict[str, object]]:
        """Stream chat events."""


@dataclass(frozen=True)
class _StreamConfig:
    """Configuration for a streaming chat response."""

    conversation_id: UUID
    content: str
    db: AsyncSession
    agent_builder: Callable[[], _ChatAgent]
    last_event_id: int | None = None


def _sanitize_chunk(chunk: dict[str, object]) -> dict[str, object]:
    """Make an agent event chunk JSON-serializable.

    Deep Agents subagents may return ``ToolMessage`` or other LangChain
    message objects as the ``result`` of a ``tool_result`` event. This
    replaces any non-serializable value with its string representation.
    """
    result = chunk.get("result")
    if result is not None and not isinstance(
        result, str | int | float | bool | list | dict | None
    ):
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


async def _yield_error(  # noqa: RUF029 — async generator needed for async for callers
    event_id: int,
    message: str,
) -> AsyncIterator[str]:
    """Yield a single SSE error event."""
    yield _format_sse_event(event_id, {"type": SSE_EVENT_ERROR, "content": message})


class _StreamState:
    """Mutable state for a chat streaming session."""

    def __init__(self, conversation_id: UUID) -> None:
        self.conversation_id: UUID = conversation_id
        self.event_id: int = 0
        self.full_response: str = ""


async def _setup_message_repos(
    db: AsyncSession,
    conversation_id: UUID,
    content: str,
) -> tuple[PostgresMessageRepository, object | None]:
    """Set up repos, validate conversation, persist user message."""
    conv_repo = PostgresConversationRepository(db)
    msg_repo = PostgresMessageRepository(db)
    conversation_service = ConversationService(
        conversation_repository=conv_repo,
        message_repository=msg_repo,
        max_context_tokens=4000,
    )
    conversation = await conversation_service.get_conversation(conversation_id)
    if conversation is None:
        return msg_repo, None
    user_message = Message(
        role=MessageRole.USER,
        content=content.strip(),
        conversation_id=conversation_id,
    )
    await msg_repo.create(user_message)
    await db.commit()
    return msg_repo, conversation


async def _drain_queue(queue: asyncio.Queue[str]) -> AsyncIterator[str]:
    """Drain remaining events from the queue."""
    while not queue.empty():
        yield await queue.get()


def _build_streaming_context(
    last_event_id: int | None,
    queue: asyncio.Queue[str],
    stop_event: asyncio.Event,
) -> tuple[int, str, asyncio.Task[None]]:
    """Build event_id, full_response buffer, and start keep-alive task."""
    event_id = last_event_id if last_event_id is not None else 0
    keep_alive = asyncio.create_task(
        _keep_alive_task(queue, SSE_KEEP_ALIVE_INTERVAL_SECONDS, stop_event)
    )
    return event_id, "", keep_alive


async def _persist_assistant_response(
    repos: tuple[PostgresMessageRepository, AsyncSession],
    ctx: _StreamState,
    queue: asyncio.Queue[str],
) -> int:
    """Persist the assistant response and emit completion event."""
    msg_repo, db = repos
    assistant_message = Message(
        role=MessageRole.ASSISTANT,
        content=ctx.full_response,
        conversation_id=ctx.conversation_id,
        sources=[],
    )
    await msg_repo.create(assistant_message)
    await db.commit()
    ctx.event_id += 1
    await queue.put(_format_sse_event(ctx.event_id, {"type": SSE_EVENT_COMPLETE}))
    return ctx.event_id


def _stop_keep_alive(
    stop_event: asyncio.Event,
    keep_alive: asyncio.Task[None],
) -> None:
    """Stop the keep-alive task and await its cancellation."""
    stop_event.set()
    keep_alive.cancel()


async def _run_stream(
    source: tuple[Callable[[], _ChatAgent], str],
    ctx: _StreamState,
    queue: asyncio.Queue[str],
) -> tuple[int, str]:
    """Run the agent stream, pushing token events to the queue."""
    agent_builder, content = source
    agent = agent_builder()
    chat_ctx = _ChatContext(
        message=content.strip(),
        conversation_id=ctx.conversation_id,
        stream=True,
        persist_messages=False,
    )
    async for chunk in agent.chat(chat_ctx):
        safe_chunk = _sanitize_chunk(chunk)
        ctx.event_id += 1
        await queue.put(_format_sse_event(ctx.event_id, safe_chunk))
        if safe_chunk.get("type") == SSE_EVENT_TOKEN:
            token_content = safe_chunk.get("content", "")
            if isinstance(token_content, str):
                ctx.full_response += token_content
    return ctx.event_id, ctx.full_response


async def stream_chat_response(
    config: _StreamConfig,
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
    """
    if not config.content or not config.content.strip():
        async for event in _yield_error(0, ERR_EMPTY_MESSAGE):
            yield event
        return

    msg_repo, conversation = await _setup_message_repos(
        config.db, config.conversation_id, config.content
    )
    if conversation is None:
        async for event in _yield_error(
            0, f"Conversation {config.conversation_id} not found"
        ):
            yield event
        return

    queue: asyncio.Queue[str] = asyncio.Queue()
    stop_event = asyncio.Event()
    stream_ctx = _StreamState(config.conversation_id)
    _, _, keep_alive = _build_streaming_context(config.last_event_id, queue, stop_event)
    stream_ctx.event_id = (
        config.last_event_id if config.last_event_id is not None else 0
    )

    try:
        _, _ = await _run_stream(
            (config.agent_builder, config.content), stream_ctx, queue
        )
        await _persist_assistant_response((msg_repo, config.db), stream_ctx, queue)
    except Exception as exc:
        stream_ctx.event_id += 1
        await queue.put(
            _format_sse_event(
                stream_ctx.event_id,
                {
                    "type": SSE_EVENT_ERROR,
                    "content": f"Error processing message: {exc!s}",
                },
            )
        )
    finally:
        _stop_keep_alive(stop_event, keep_alive)
        await asyncio.gather(keep_alive, return_exceptions=True)
        async for event in _drain_queue(queue):
            yield event

    async for event in _drain_queue(queue):
        yield event
