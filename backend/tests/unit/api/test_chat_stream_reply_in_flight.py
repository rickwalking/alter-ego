"""The stream route refuses a second turn while a reply is being written.

Feature file: tests/features/chat_disconnect_reply.feature
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from rag_backend.api.routes import chat_stream
from rag_backend.domain.constants.chat_stream import CHAT_TURN_IN_FLIGHT


def test_refuses_with_409_while_a_reply_is_written() -> None:
    """A new message gets 409 before any stream starts.

    Scenario: One reply at a time per conversation
    """
    with (
        patch.object(chat_stream, "conversation_reply_in_flight", return_value=True),
        pytest.raises(HTTPException) as refused,
    ):
        chat_stream._refuse_while_reply_in_flight(uuid4())

    assert refused.value.status_code == status.HTTP_409_CONFLICT
    assert refused.value.detail == CHAT_TURN_IN_FLIGHT


def test_lets_a_message_through_when_no_reply_is_written() -> None:
    """No reply in flight, no refusal.

    Scenario: One reply at a time per conversation
    """
    with patch.object(chat_stream, "conversation_reply_in_flight", return_value=False):
        chat_stream._refuse_while_reply_in_flight(uuid4())
