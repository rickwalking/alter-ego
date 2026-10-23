"""Conversations are titled from their first message.

Feature file: tests/features/conversation_titles.feature
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rag_backend.application.services.chat_stream_service import _setup_message_repos
from rag_backend.domain.constants.conversation import CONVERSATION_TITLE_MAX_LENGTH
from rag_backend.domain.models import Conversation

_SERVICE = "rag_backend.application.services.chat_stream_service"


def test_first_message_titles_an_untitled_conversation() -> None:
    """The first message becomes the title, whitespace collapsed.

    Scenario: The first message titles an untitled conversation
    """
    conversation = Conversation()

    changed = conversation.ensure_title_from(
        "  What do you think   about microservices?"
    )

    assert changed is True
    assert conversation.title == "What do you think about microservices?"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("x" * 80, "x" * (CONVERSATION_TITLE_MAX_LENGTH - 1) + "…"),
        ("First line\nsecond line", "First line"),
        ("y" * CONVERSATION_TITLE_MAX_LENGTH, "y" * CONVERSATION_TITLE_MAX_LENGTH),
        (
            "z" * (CONVERSATION_TITLE_MAX_LENGTH - 2) + " tail of the question",
            "z" * (CONVERSATION_TITLE_MAX_LENGTH - 2) + "…",
        ),
    ],
)
def test_title_is_one_short_line(message: str, expected: str) -> None:
    """Long titles are cut at the limit with an ellipsis; only the first line counts.

    Scenario: A long or multi-line first message gives a short one-line title
    """
    conversation = Conversation()
    conversation.ensure_title_from(message)
    assert conversation.title == expected
    assert len(conversation.title) <= CONVERSATION_TITLE_MAX_LENGTH


@pytest.mark.parametrize("title", ["Pauta de outubro", None])
def test_existing_title_or_blank_message_changes_nothing(title: str | None) -> None:
    """A titled conversation keeps its title; a blank message never titles one.

    Scenario: An existing title is never replaced
    """
    conversation = Conversation(title=title)
    message = "another question" if title else "   "

    assert conversation.ensure_title_from(message) is False
    assert conversation.title == title


def test_whitespace_title_counts_as_untitled() -> None:
    """A title of only spaces is replaced by the first message.

    Scenario: The first message titles an untitled conversation
    """
    conversation = Conversation(title="   ")

    assert conversation.ensure_title_from("Hello there") is True
    assert conversation.title == "Hello there"


@pytest.mark.asyncio
@pytest.mark.parametrize(("title", "updates"), [(None, 1), ("Kept", 0)])
async def test_stream_titles_only_untitled_conversations(
    title: str | None, updates: int
) -> None:
    """The stream saves a title for a new conversation and leaves titled ones alone.

    Scenario: The first message titles an untitled conversation
    """
    conversation = Conversation(id=uuid4(), title=title)
    with (
        patch(f"{_SERVICE}.PostgresConversationRepository") as conv_repo_cls,
        patch(f"{_SERVICE}.PostgresMessageRepository", return_value=AsyncMock()),
        patch(f"{_SERVICE}.ConversationService") as service_cls,
    ):
        service = MagicMock()
        service.get_conversation = AsyncMock(return_value=conversation)
        service_cls.return_value = service
        conv_repo = AsyncMock()
        conv_repo_cls.return_value = conv_repo

        await _setup_message_repos(AsyncMock(), conversation.id, "Who are you?")

    assert conv_repo.update.await_count == updates
    assert conversation.title == (title or "Who are you?")
