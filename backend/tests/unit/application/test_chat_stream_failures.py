"""A failed chat turn is logged, answered with an apology and never leaks details.

Feature file: tests/features/chat_errors.feature
"""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from rag_backend.application.services.chat_stream_service import (
    _ChatContext,
    _StreamConfig,
    stream_chat_response,
)
from rag_backend.domain.constants.chat_stream import CHAT_FAILED_REPLY
from rag_backend.domain.models import Conversation, MessageRole

_SERVICE = "rag_backend.application.services.chat_stream_service"
_LEAKY_ERROR = (
    "Recursion limit of 25 reached without hitting a stop condition. "
    "For troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/"
)


class _FailingAgent:
    """Streams one token, then raises the kind of error LangGraph raises."""

    async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
        del ctx
        yield {"type": "token", "content": "partial"}
        raise RuntimeError(_LEAKY_ERROR)


async def _run_failing_turn(
    msg_repo: AsyncMock, db: AsyncMock | None = None
) -> tuple[list[str], list[dict[str, object]]]:
    """Stream one failing turn; return the SSE frames and the captured logs."""
    conversation = Conversation(id=uuid4(), title="Chat")
    db = db or AsyncMock(spec=AsyncSession)
    with (
        patch(f"{_SERVICE}.PostgresConversationRepository"),
        patch(f"{_SERVICE}.PostgresMessageRepository", return_value=msg_repo),
        patch(f"{_SERVICE}.ConversationService") as service_cls,
        capture_logs() as logs,
    ):
        service = MagicMock()
        service.get_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value = service
        frames = [
            frame
            async for frame in stream_chat_response(
                _StreamConfig(
                    conversation_id=conversation.id,
                    content="Who are you?",
                    db=db,
                    agent_builder=lambda _db: _FailingAgent(),
                )
            )
            if not frame.startswith(": ping")
        ]
    return frames, logs


@pytest.mark.asyncio
async def test_failure_is_logged_with_conversation_and_type() -> None:
    """The server log carries the failure, its type and the conversation."""
    # Scenario: A failed reply is logged on the server
    _, logs = await _run_failing_turn(AsyncMock())

    failure = next(log for log in logs if log["event"] == "chat_stream_failed")
    assert failure["error_type"] == "RuntimeError"
    assert failure["log_level"] == "error"
    assert failure["conversation_id"]


@pytest.mark.asyncio
async def test_client_gets_a_generic_message() -> None:
    """The error event carries the plain apology, not the exception text."""
    # Scenario: The visitor sees a plain message, never the technical error
    frames, _ = await _run_failing_turn(AsyncMock())

    error_frame = frames[-1]
    assert '"type": "error"' in error_frame
    assert CHAT_FAILED_REPLY in error_frame
    assert "Recursion limit" not in "".join(frames)
    assert "docs.langchain.com" not in "".join(frames)


@pytest.mark.asyncio
async def test_failed_turn_is_answered_with_an_apology() -> None:
    """User message, then the apology; the partial reply is never saved."""
    # Scenario: A failed turn leaves no unanswered question behind
    msg_repo = AsyncMock()
    await _run_failing_turn(msg_repo)

    saved = [call.args[0] for call in msg_repo.create.call_args_list]
    assert [message.role for message in saved] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert saved[1].content == CHAT_FAILED_REPLY
    assert all("partial" not in message.content for message in saved)


@pytest.mark.asyncio
async def test_error_event_survives_a_failed_apology_save() -> None:
    """When the apology cannot be saved it is logged and the client still hears back."""
    # Scenario: The visitor still gets the error event when the apology cannot be saved
    msg_repo = AsyncMock()
    msg_repo.create.side_effect = [MagicMock(), RuntimeError("db down")]
    frames, logs = await _run_failing_turn(msg_repo)

    assert any(log["event"] == "chat_stream_failed_turn_not_saved" for log in logs)
    assert CHAT_FAILED_REPLY in frames[-1]


@pytest.mark.asyncio
async def test_partial_writes_are_rolled_back_before_the_apology() -> None:
    """The session is rolled back first, so a flushed partial reply is never committed."""
    # Scenario: A failed turn leaves no unanswered question behind
    calls: list[str] = []
    db = AsyncMock(spec=AsyncSession)
    db.rollback.side_effect = lambda: calls.append("rollback")
    db.commit.side_effect = lambda: calls.append("commit")
    msg_repo = AsyncMock()
    msg_repo.create.side_effect = lambda message: calls.append(f"save:{message.role}")

    await _run_failing_turn(msg_repo, db)

    assert calls == [
        "save:user",
        "commit",
        "rollback",
        "save:assistant",
        "commit",
    ]
