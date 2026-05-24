"""Unit tests for chat_stream_service.

# Feature: SSE Chat Streaming Service
# Scenario: Empty message returns error event
#   Given an empty message content
#   When stream_chat_response is called
#   Then it yields an error SSE event
#
# Scenario: Nonexistent conversation returns error event
#   Given a conversation id that does not exist
#   When stream_chat_response is called
#   Then it yields an error SSE event
#
# Scenario: Successful token streaming
#   Given a valid conversation and agent that yields tokens
#   When stream_chat_response is called
#   Then it yields token events followed by a complete event
#   And persists user and assistant messages
#
# Scenario: Agent error during streaming
#   Given an agent that raises an exception
#   When stream_chat_response is called
#   Then it yields an error event
#   And does not persist an assistant message
#
# Scenario: Tool result sanitization
#   Given an agent that returns non-serializable tool results
#   When stream_chat_response is called
#   Then the result is converted to a string
#
# Scenario: Keep-alive pings
#   Given a slow agent
#   When stream_chat_response is called
#   Then keep-alive ping comments are yielded periodically
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_EMPTY_MESSAGE,
    SSE_EVENT_COMPLETE,
    SSE_EVENT_ERROR,
    SSE_EVENT_TOKEN,
    SSE_EVENT_TOOL_RESULT,
)
from rag_backend.application.services.chat_stream_service import (
    _format_sse_event,
    _keep_alive_task,
    _sanitize_chunk,
    stream_chat_response,
)
from rag_backend.domain.models import Conversation, MessageRole


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_conversation():
    """Create a mock conversation."""
    return Conversation(
        id=uuid4(),
        title="Test Chat",
        created_at="2026-05-22T00:00:00Z",
        updated_at="2026-05-22T00:00:00Z",
    )


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, chunks: list[dict] | None = None, error: Exception | None = None):
        self.chunks = chunks or []
        self.error = error

    async def chat(
        self,
        *,
        message: str,
        conversation_id: UUID,
        stream: bool,
        persist_messages: bool,
    ) -> AsyncIterator[dict]:
        if self.error:
            raise self.error
        for chunk in self.chunks:
            yield chunk


def _parse_sse_event(text: str) -> dict:
    """Parse a single SSE event string into a dict."""
    lines = text.strip().split("\n")
    data = ""
    for line in lines:
        if line.startswith("data: "):
            data = line[6:]
    return json.loads(data)


class TestStreamChatResponse:
    """Tests for stream_chat_response function."""

    @pytest.mark.asyncio
    async def test_empty_message_yields_error(self, mock_db):
        """Given empty content, when streaming, then yields error event."""
        events = []
        async for event in stream_chat_response(
            conversation_id=uuid4(),
            content="",
            db=mock_db,
            agent_builder=lambda: MockAgent(),
        ):
            events.append(event)

        assert len(events) == 1
        parsed = _parse_sse_event(events[0])
        assert parsed["type"] == SSE_EVENT_ERROR
        assert parsed["content"] == ERR_EMPTY_MESSAGE
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_message_yields_error(self, mock_db):
        """Given whitespace-only content, when streaming, then yields error event."""
        events = []
        async for event in stream_chat_response(
            conversation_id=uuid4(),
            content="   ",
            db=mock_db,
            agent_builder=lambda: MockAgent(),
        ):
            events.append(event)

        assert len(events) == 1
        parsed = _parse_sse_event(events[0])
        assert parsed["type"] == SSE_EVENT_ERROR

    @pytest.mark.asyncio
    async def test_nonexistent_conversation_yields_error(self, mock_db):
        """Given missing conversation, when streaming, then yields error event."""
        conv_id = uuid4()

        with (
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresConversationRepository"
            ) as mock_conv_repo_cls,
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresMessageRepository"
            ) as mock_msg_repo_cls,
            patch(
                "rag_backend.application.services.chat_stream_service.ConversationService"
            ) as mock_service_cls,
        ):
            mock_service = MagicMock()
            mock_service.get_conversation = AsyncMock(return_value=None)
            mock_service_cls.return_value = mock_service

            events = []
            async for event in stream_chat_response(
                conversation_id=conv_id,
                content="Hello",
                db=mock_db,
                agent_builder=lambda: MockAgent(),
            ):
                events.append(event)

        assert len(events) == 1
        parsed = _parse_sse_event(events[0])
        assert parsed["type"] == SSE_EVENT_ERROR
        assert "not found" in parsed["content"].lower()

    @pytest.mark.asyncio
    async def test_successful_streaming_yields_tokens_and_complete(
        self, mock_db, mock_conversation
    ):
        """Given valid agent, when streaming, then yields tokens and complete event."""
        conv_id = mock_conversation.id
        agent = MockAgent(
            chunks=[
                {"type": SSE_EVENT_TOKEN, "content": "Hello"},
                {"type": SSE_EVENT_TOKEN, "content": " world"},
            ]
        )

        with (
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresConversationRepository"
            ),
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresMessageRepository"
            ) as mock_msg_repo_cls,
            patch(
                "rag_backend.application.services.chat_stream_service.ConversationService"
            ) as mock_service_cls,
        ):
            mock_service = MagicMock()
            mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
            mock_service_cls.return_value = mock_service

            mock_msg_repo = AsyncMock()
            mock_msg_repo_cls.return_value = mock_msg_repo

            events = []
            async for event in stream_chat_response(
                conversation_id=conv_id,
                content="Hi",
                db=mock_db,
                agent_builder=lambda: agent,
            ):
                # Skip keep-alive pings
                if not event.startswith(": ping"):
                    events.append(event)

        # Should have token events + complete event
        parsed_events = [_parse_sse_event(e) for e in events]
        types = [e["type"] for e in parsed_events]
        assert SSE_EVENT_TOKEN in types
        assert SSE_EVENT_COMPLETE in types

        # Verify user message was persisted
        mock_msg_repo.create.assert_called()
        call_args = mock_msg_repo.create.call_args_list[0][0][0]
        assert call_args.role == MessageRole.USER
        assert call_args.content == "Hi"

        # Verify assistant message was persisted
        assistant_call = mock_msg_repo.create.call_args_list[1][0][0]
        assert assistant_call.role == MessageRole.ASSISTANT
        assert assistant_call.content == "Hello world"

    @pytest.mark.asyncio
    async def test_agent_error_yields_error_event(self, mock_db, mock_conversation):
        """Given agent that raises, when streaming, then yields error event."""
        agent = MockAgent(error=RuntimeError("Agent failed"))

        with (
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresConversationRepository"
            ),
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresMessageRepository"
            ) as mock_msg_repo_cls,
            patch(
                "rag_backend.application.services.chat_stream_service.ConversationService"
            ) as mock_service_cls,
        ):
            mock_service = MagicMock()
            mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
            mock_service_cls.return_value = mock_service

            mock_msg_repo = AsyncMock()
            mock_msg_repo_cls.return_value = mock_msg_repo

            events = []
            async for event in stream_chat_response(
                conversation_id=mock_conversation.id,
                content="Hi",
                db=mock_db,
                agent_builder=lambda: agent,
            ):
                if not event.startswith(": ping"):
                    events.append(event)

        parsed_events = [_parse_sse_event(e) for e in events]
        assert any(e["type"] == SSE_EVENT_ERROR for e in parsed_events)
        error_event = next(e for e in parsed_events if e["type"] == SSE_EVENT_ERROR)
        assert "Agent failed" in error_event["content"]

        # Assistant message should NOT be persisted on error
        assert mock_msg_repo.create.call_count == 1  # Only user message

    @pytest.mark.asyncio
    async def test_tool_result_sanitization(self, mock_db, mock_conversation):
        """Given non-serializable tool result, when streaming, then result is stringified."""

        class NonSerializable:
            def __str__(self):
                return "tool-output"

        agent = MockAgent(
            chunks=[
                {"type": SSE_EVENT_TOOL_RESULT, "tool": "test_tool", "result": NonSerializable()},
            ]
        )

        with (
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresConversationRepository"
            ),
            patch(
                "rag_backend.application.services.chat_stream_service.PostgresMessageRepository"
            ) as mock_msg_repo_cls,
            patch(
                "rag_backend.application.services.chat_stream_service.ConversationService"
            ) as mock_service_cls,
        ):
            mock_service = MagicMock()
            mock_service.get_conversation = AsyncMock(return_value=mock_conversation)
            mock_service_cls.return_value = mock_service

            mock_msg_repo = AsyncMock()
            mock_msg_repo_cls.return_value = mock_msg_repo

            events = []
            async for event in stream_chat_response(
                conversation_id=mock_conversation.id,
                content="Run tool",
                db=mock_db,
                agent_builder=lambda: agent,
            ):
                if not event.startswith(": ping"):
                    events.append(event)

        parsed = _parse_sse_event(events[0])
        assert parsed["type"] == SSE_EVENT_TOOL_RESULT
        assert parsed["result"] == "tool-output"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_sanitize_chunk_with_serializable_result(self):
        """Given serializable result, when sanitizing, then chunk is unchanged."""
        chunk = {"type": "tool_result", "result": {"key": "value"}}
        assert _sanitize_chunk(chunk) == chunk

    def test_sanitize_chunk_with_non_serializable_result(self):
        """Given non-serializable result, when sanitizing, then result is stringified."""

        class FakeObj:
            def __str__(self):
                return "fake-output"

        chunk = {"type": "tool_result", "result": FakeObj()}
        sanitized = _sanitize_chunk(chunk)
        assert sanitized["result"] == "fake-output"

    def test_sanitize_chunk_with_none_result(self):
        """Given None result, when sanitizing, then chunk is unchanged."""
        chunk = {"type": "token", "content": "hello"}
        assert _sanitize_chunk(chunk) == chunk

    def test_format_sse_event(self):
        """Given event data, when formatting, then produces valid SSE format."""
        event = _format_sse_event(42, {"type": "token", "content": "hi"})
        assert event == 'id: 42\ndata: {"type": "token", "content": "hi"}\n\n'

    @pytest.mark.asyncio
    async def test_keep_alive_task_sends_pings(self):
        """Given keep-alive task, when running, then sends ping comments."""
        queue = asyncio.Queue()
        stop_event = asyncio.Event()

        task = asyncio.create_task(_keep_alive_task(queue, 0.05, stop_event))

        # Wait for at least one ping
        await asyncio.sleep(0.08)
        stop_event.set()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        pings = []
        while not queue.empty():
            pings.append(await queue.get())

        assert any(ping == ": ping\n\n" for ping in pings)

    @pytest.mark.asyncio
    async def test_keep_alive_task_stops_on_event(self):
        """Given stop event, when set, then keep-alive stops immediately."""
        queue = asyncio.Queue()
        stop_event = asyncio.Event()

        task = asyncio.create_task(_keep_alive_task(queue, 1.0, stop_event))
        stop_event.set()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Should not have any pings since we stopped immediately
        assert queue.empty()
