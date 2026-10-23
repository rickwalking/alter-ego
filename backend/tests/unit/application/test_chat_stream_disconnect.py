"""A reply is saved even when the client disconnects mid-generation.

Feature file: tests/features/chat_disconnect_reply.feature
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import anyio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services import chat_stream_service
from rag_backend.application.services.chat_stream_service import (
    _ChatContext,
    _StreamConfig,
    stream_chat_response,
)
from rag_backend.domain.constants.chat_stream import CHAT_FAILED_REPLY
from rag_backend.domain.models import Conversation, Message, MessageRole

_SERVICE = "rag_backend.application.services.chat_stream_service"


def _gated_agent(release: asyncio.Event, *, fail: bool) -> type:
    """An agent that writes once ``release`` is set, then finishes or fails."""

    class _GatedAgent:
        async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
            del ctx
            yield {"type": "token", "content": "Once upon"}
            await release.wait()
            if fail:
                raise RuntimeError("upstream model error")
            yield {"type": "token", "content": " a time."}

    return _GatedAgent


async def _disconnect_mid_reply(*, fail: bool) -> tuple[list[str], AsyncMock]:
    """Stream a turn, drop the client mid-reply, let the agent end; return saves."""
    conversation = Conversation(id=uuid4(), title="Chat")
    saved: list[str] = []
    turn_db = AsyncMock(spec=AsyncSession)

    def repo_for(db: object) -> AsyncMock:
        repo = AsyncMock()

        async def create(message: Message) -> Message:
            await asyncio.sleep(0)
            if db is turn_db and message.role == MessageRole.ASSISTANT:
                saved.append(message.content)
            return message

        repo.create.side_effect = create
        return repo

    @asynccontextmanager
    async def turn_session() -> AsyncIterator[AsyncSession]:
        yield turn_db

    release = asyncio.Event()
    with (
        patch(f"{_SERVICE}.PostgresConversationRepository"),
        patch(f"{_SERVICE}.PostgresMessageRepository", side_effect=repo_for),
        patch(f"{_SERVICE}.ConversationService") as service_cls,
    ):
        service = MagicMock()
        service.get_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value = service

        async def consume() -> None:
            async for _ in stream_chat_response(
                _StreamConfig(
                    conversation_id=conversation.id,
                    content="Tell me a story",
                    db=AsyncMock(spec=AsyncSession),
                    agent_builder=_gated_agent(release, fail=fail),
                    session_factory=turn_session,
                )
            ):
                pass

        async with anyio.create_task_group() as group:
            group.start_soon(consume)
            await anyio.sleep(0.05)
            group.cancel_scope.cancel()

        assert saved == []
        release.set()
        await asyncio.gather(*chat_stream_service._DETACHED_TURNS)
    return saved, turn_db


@pytest.mark.asyncio
async def test_reply_is_saved_after_the_client_disconnects() -> None:
    """The whole reply is saved in the turn's own session after the disconnect.

    Scenario: The reply is saved after the client disconnects
    """
    saved, turn_db = await _disconnect_mid_reply(fail=False)

    assert saved == ["Once upon a time."]
    turn_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_failure_after_disconnect_saves_an_apology() -> None:
    """A failure after the disconnect still answers the question.

    Scenario: A reply that fails after the client disconnects is answered with an apology
    """
    saved, _ = await _disconnect_mid_reply(fail=True)

    assert saved == [CHAT_FAILED_REPLY]
