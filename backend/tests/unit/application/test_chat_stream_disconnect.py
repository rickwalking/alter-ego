"""A reply is streamed live, saved even when the client disconnects, one per conversation.

Feature file: tests/features/chat_disconnect_reply.feature
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import anyio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services import chat_turns
from rag_backend.application.services.chat_stream_service import (
    _ChatContext,
    _StreamConfig,
    stream_chat_response,
)
from rag_backend.application.services.chat_turns import drain_detached_turns
from rag_backend.domain.constants.chat_stream import (
    CHAT_FAILED_REPLY,
    CHAT_TURN_IN_FLIGHT,
)
from rag_backend.domain.models import Conversation, Message, MessageRole

_SERVICE = "rag_backend.application.services.chat_stream_service"


@dataclass
class _Turn:
    """What one streamed turn did: the agent's sessions and the saved replies."""

    release: asyncio.Event = field(default_factory=asyncio.Event)
    turn_db: AsyncMock = field(default_factory=lambda: AsyncMock(spec=AsyncSession))
    request_db: AsyncMock = field(default_factory=lambda: AsyncMock(spec=AsyncSession))
    agent_sessions: list[object] = field(default_factory=list)
    saved: list[str] = field(default_factory=list)
    conversation_id: UUID = field(default_factory=uuid4)
    fail: bool = False

    def builder(self) -> Callable[[AsyncSession], object]:
        """An agent that writes once released, then finishes or fails."""
        turn = self

        class _GatedAgent:
            async def chat(self, ctx: _ChatContext) -> AsyncIterator[dict[str, object]]:
                del ctx
                yield {"type": "token", "content": "Once upon"}
                await turn.release.wait()
                if turn.fail:
                    raise RuntimeError("upstream model error")
                yield {"type": "token", "content": " a time."}

        def build(db: AsyncSession) -> _GatedAgent:
            turn.agent_sessions.append(db)
            return _GatedAgent()

        return build

    def repo_for(self, db: object) -> AsyncMock:
        """A message repository that records the assistant replies saved via ``db``."""
        repo = AsyncMock()

        async def create(message: Message) -> Message:
            await asyncio.sleep(0)
            if db is self.turn_db and message.role == MessageRole.ASSISTANT:
                self.saved.append(message.content)
            return message

        repo.create.side_effect = create
        return repo

    def stream(self) -> AsyncIterator[str]:
        """The SSE stream of this turn, with its own session factory."""

        @asynccontextmanager
        async def turn_session() -> AsyncIterator[AsyncSession]:
            yield self.turn_db

        return stream_chat_response(
            _StreamConfig(
                conversation_id=self.conversation_id,
                content="Tell me a story",
                db=self.request_db,
                agent_builder=self.builder(),
                session_factory=turn_session,
            )
        )


@contextmanager
def _patched(turn: _Turn) -> Iterator[None]:
    with (
        patch(f"{_SERVICE}.PostgresConversationRepository"),
        patch(f"{_SERVICE}.PostgresMessageRepository", side_effect=turn.repo_for),
        patch(f"{_SERVICE}.ConversationService") as service_cls,
    ):
        service = MagicMock()
        service.get_conversation = AsyncMock(
            return_value=Conversation(id=turn.conversation_id, title="Chat")
        )
        service_cls.return_value = service
        yield


async def _disconnect_mid_reply(turn: _Turn) -> None:
    """Drop the client mid-reply (Starlette cancels its task group), then release."""

    async def consume() -> None:
        async for _ in turn.stream():
            pass

    async with anyio.create_task_group() as group:
        group.start_soon(consume)
        await anyio.sleep(0.05)
        group.cancel_scope.cancel()
    assert turn.saved == []
    turn.release.set()
    await asyncio.gather(*chat_turns.DETACHED_TURNS)


@pytest.mark.asyncio
async def test_reply_is_saved_after_the_client_disconnects() -> None:
    """The whole reply is saved in the turn's own session after the disconnect.

    Scenario: The reply is saved after the client disconnects
    """
    turn = _Turn()
    with _patched(turn):
        await _disconnect_mid_reply(turn)

    assert turn.saved == ["Once upon a time."]
    turn.turn_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_agent_runs_on_the_turns_own_session() -> None:
    """The agent is built on the turn's session, never the request's.

    Scenario: The reply is saved after the client disconnects
    """
    turn = _Turn()
    with _patched(turn):
        await _disconnect_mid_reply(turn)

    assert turn.agent_sessions == [turn.turn_db]


@pytest.mark.asyncio
async def test_failure_after_disconnect_saves_an_apology() -> None:
    """A failure after the disconnect still answers the question.

    Scenario: A reply that fails after the client disconnects is answered with an apology
    """
    turn = _Turn(fail=True)
    with _patched(turn):
        await _disconnect_mid_reply(turn)

    assert turn.saved == [CHAT_FAILED_REPLY]


@pytest.mark.asyncio
async def test_first_token_reaches_the_client_before_the_turn_ends() -> None:
    """Tokens stream live: the first one arrives while the agent is still writing.

    Scenario: Tokens reach the client while the reply is written
    """
    turn = _Turn()
    with _patched(turn):
        events = turn.stream()
        first = await asyncio.wait_for(anext(events), timeout=1)
        assert "Once upon" in first
        assert turn.saved == []
        turn.release.set()
        rest = [event async for event in events]

    assert any('"complete"' in event for event in rest)
    assert turn.saved == ["Once upon a time."]


@pytest.mark.asyncio
async def test_second_turn_waits_for_the_reply_being_written() -> None:
    """While a reply is written, a new turn for the same conversation is refused.

    Scenario: One reply at a time per conversation
    """
    first = _Turn()
    second = _Turn(conversation_id=first.conversation_id)
    with _patched(first):
        events = first.stream()
        await asyncio.wait_for(anext(events), timeout=1)

        refused = [event async for event in second.stream()]

        first.release.set()
        _ = [event async for event in events]
        await asyncio.gather(*chat_turns.DETACHED_TURNS)

    assert len(refused) == 1
    assert CHAT_TURN_IN_FLIGHT in refused[0]
    assert second.agent_sessions == []
    assert not chat_turns.conversation_turn_in_flight(first.conversation_id)


@pytest.mark.asyncio
async def test_shutdown_cancels_a_stuck_turn_and_saves_the_apology() -> None:
    """Draining at shutdown cancels a turn past the timeout; it saves the apology.

    Scenario: Shutdown answers the replies still being written
    """
    turn = _Turn()
    with _patched(turn):
        events = turn.stream()
        await asyncio.wait_for(anext(events), timeout=1)
        await events.aclose()

        await drain_detached_turns(0.05)

    assert turn.saved == [CHAT_FAILED_REPLY]
    assert not chat_turns.DETACHED_TURNS
    assert not chat_turns.conversation_turn_in_flight(turn.conversation_id)
