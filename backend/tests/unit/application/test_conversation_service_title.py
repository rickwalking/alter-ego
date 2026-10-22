"""ConversationService.generate_title keeps titles within the length limit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from rag_backend.application.services.conversation_service import (
    MAX_TITLE_LENGTH,
    ConversationService,
)


def _service(first_message: str) -> tuple[ConversationService, MagicMock]:
    message = MagicMock()
    message.content = first_message
    messages = MagicMock()
    messages.get_by_conversation = AsyncMock(return_value=[message])
    conversation = MagicMock()
    conversations = MagicMock()
    conversations.get_by_id = AsyncMock(return_value=conversation)
    conversations.update = AsyncMock()
    return ConversationService(conversations, messages), conversation


async def test_long_generated_title_is_cut_to_the_limit() -> None:
    """A title over the limit is cut and ends with an ellipsis."""
    service, conversation = _service("How do agents plan?")
    generated = '"' + "x" * (MAX_TITLE_LENGTH + 20) + '"'

    title = await service.generate_title(uuid4(), AsyncMock(return_value=generated))

    assert len(title) == MAX_TITLE_LENGTH
    assert title.endswith("...")
    conversation.update_title.assert_called_once_with(title)


async def test_short_generated_title_is_kept_unquoted() -> None:
    """A title within the limit is stored without its quotes."""
    service, conversation = _service("How do agents plan?")

    title = await service.generate_title(
        uuid4(), AsyncMock(return_value='"Agent planning"')
    )

    assert title == "Agent planning"
    conversation.update_title.assert_called_once_with("Agent planning")
