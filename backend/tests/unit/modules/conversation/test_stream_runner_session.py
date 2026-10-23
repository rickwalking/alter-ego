"""The stream runner gives each reply its own session when it can.

Feature file: tests/features/chat_disconnect_reply.feature
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.conversation.application.streaming import StreamChatCommand
from rag_backend.modules.conversation.infrastructure.stream_runner import (
    LegacyStreamChatRunner,
)

_RUNNER = "rag_backend.modules.conversation.infrastructure.stream_runner"


def _run_with(get_session_maker: MagicMock) -> MagicMock:
    """Run one command through the runner and return the patched service."""
    command = StreamChatCommand(
        conversation_id=uuid4(), content="hi", last_event_id=None
    )
    builder = MagicMock()
    with (
        patch(f"{_RUNNER}.get_session_maker", get_session_maker),
        patch(f"{_RUNNER}.stream_chat_response") as stream,
    ):
        LegacyStreamChatRunner(AsyncMock(spec=AsyncSession)).run(command, builder)
    return stream


def test_reply_gets_its_own_session_factory() -> None:
    """The reply's session comes from the engine's session maker.

    Scenario: The reply is saved after the client disconnects
    """
    maker = MagicMock()
    stream = _run_with(MagicMock(return_value=maker))

    assert stream.call_args.args[0].session_factory is maker


def test_without_an_engine_the_reply_uses_the_request_session() -> None:
    """No engine (tests overriding the session): no factory, the request session.

    Scenario: The reply is saved after the client disconnects
    """
    stream = _run_with(MagicMock(side_effect=RuntimeError("not initialised")))

    assert stream.call_args.args[0].session_factory is None
