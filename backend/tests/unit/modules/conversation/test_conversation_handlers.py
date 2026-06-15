"""Unit tests for the conversation command/query handlers (AE-0101).

Feature: Conversation routes delegate to handlers behind the facade
See tests/features/conversations.feature (byte-identical extraction scenarios).

These tests prove the handler use cases the thin ``/api/conversations`` route
adapter delegates to:

* CRUD/list/messages/title delegate to the reused ``ConversationService`` facade
  with the same arguments the legacy route used;
* writes (create/delete/generate-title) run inside the platform Unit of Work so
  the UoW is the single committer (the route never commits);
* non-streaming chat routes on ``metadata.project_id`` (rag-agent vs alter-ego),
  drains the agent's ``complete``/``sources`` events into a typed result, and
  enforces the message cap by raising ``ConversationLimitReachedError`` (which
  the route maps to 429).

No real Pinecone/OpenAI/Anthropic clients are constructed — the agent factory
and service are mocked.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.modules.conversation import (
    ChatAgentFactory,
    ChatCommand,
    Conversation,
    ConversationHandlers,
    ConversationLimitReachedError,
    ConversationService,
    CreateConversationCommand,
    DeleteConversationCommand,
    GenerateTitleCommand,
    GetConversationQuery,
    GetMessagesQuery,
    ListConversationsQuery,
    Message,
    MessageRole,
)
from rag_backend.modules.conversation.application.handlers import (
    AGENT_ORIGIN_ALTER_EGO,
    AGENT_ORIGIN_RAG,
    MAX_MESSAGES_PER_CONVERSATION,
)
from rag_backend.platform.database import UnitOfWork


class _TrackingUnitOfWork:
    """In-memory UoW double that records commit/rollback + enter/exit ordering."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.entered = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> _TrackingUnitOfWork:
        self.entered = True
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
            return
        await self.commit()


def _make_handlers(
    service: object,
    agent_factory: object,
    uow: object,
) -> ConversationHandlers:
    return ConversationHandlers(
        service=cast(ConversationService, service),
        agent_factory=cast(ChatAgentFactory, agent_factory),
        unit_of_work=cast(UnitOfWork, uow),
    )


class _StubAgent:
    """Deterministic chat agent yielding fixed complete/sources events."""

    def __init__(self, events: list[dict[str, object]]) -> None:
        self._events = events

    async def chat(self, ctx: object) -> AsyncIterator[dict[str, object]]:
        del ctx
        for event in self._events:
            yield event


# --- Write use cases commit via the UoW (single committer) ---------------------
class TestWriteHandlersCommitViaUnitOfWork:
    """Scenario: conversation writes persist via the platform UoW only."""

    @pytest.mark.asyncio
    async def test_create_commits_and_delegates_metadata(self) -> None:
        service = MagicMock()
        created = Conversation(id=uuid4(), metadata={})
        service.create_conversation = AsyncMock(return_value=created)
        uow = _TrackingUnitOfWork()
        handlers = _make_handlers(service, MagicMock(), uow)
        user_id = uuid4()

        result = await handlers.create(
            CreateConversationCommand(title="T", metadata={"k": "v"}, user_id=user_id)
        )

        assert result is created
        assert uow.entered and uow.committed and not uow.rolled_back
        service.create_conversation.assert_awaited_once_with(
            title="T", metadata={"k": "v"}, user_id=user_id
        )

    @pytest.mark.asyncio
    async def test_delete_commits_and_returns_flag(self) -> None:
        service = MagicMock()
        service.delete_conversation = AsyncMock(return_value=True)
        uow = _TrackingUnitOfWork()
        handlers = _make_handlers(service, MagicMock(), uow)
        conv_id = uuid4()

        result = await handlers.delete(DeleteConversationCommand(conv_id))

        assert result is True
        assert uow.committed
        service.delete_conversation.assert_awaited_once_with(conv_id)

    @pytest.mark.asyncio
    async def test_generate_title_commits_then_refetches(self) -> None:
        service = MagicMock()
        service.generate_title = AsyncMock(return_value="New Title")
        refreshed = Conversation(id=uuid4(), title="New Title", metadata={})
        service.get_conversation = AsyncMock(return_value=refreshed)
        uow = _TrackingUnitOfWork()
        handlers = _make_handlers(service, MagicMock(), uow)
        conv_id = uuid4()

        async def _llm(_messages: list[dict[str, str]]) -> str:
            return "New Title"

        result = await handlers.generate_title(GenerateTitleCommand(conv_id), _llm)

        assert result is refreshed
        assert uow.committed
        service.generate_title.assert_awaited_once()
        service.get_conversation.assert_awaited_once_with(conv_id)


# --- Read use cases delegate to the facade -------------------------------------
class TestReadHandlersDelegate:
    """Scenario: read handlers map onto the reused service."""

    @pytest.mark.asyncio
    async def test_list_for_owner_returns_page_with_total(self) -> None:
        service = MagicMock()
        conversations = [Conversation(id=uuid4(), metadata={})]
        service.list_conversations = AsyncMock(return_value=conversations)
        service.count_conversations_for_user = AsyncMock(return_value=5)
        handlers = _make_handlers(service, MagicMock(), _TrackingUnitOfWork())
        user_id = uuid4()

        page = await handlers.list_for_owner(
            ListConversationsQuery(
                user_id=user_id, limit=20, offset=0, origin="alter_ego"
            )
        )

        assert page.items == conversations
        assert page.total == 5
        service.count_conversations_for_user.assert_awaited_once_with(
            user_id, origin="alter_ego"
        )

    @pytest.mark.asyncio
    async def test_get_returns_conversation_or_none(self) -> None:
        service = MagicMock()
        conv = Conversation(id=uuid4(), metadata={})
        service.get_conversation = AsyncMock(return_value=conv)
        handlers = _make_handlers(service, MagicMock(), _TrackingUnitOfWork())

        result = await handlers.get(GetConversationQuery(conv.id))

        assert result is conv
        service.get_conversation.assert_awaited_once_with(conv.id)

    @pytest.mark.asyncio
    async def test_get_messages_passes_limit(self) -> None:
        service = MagicMock()
        conv_id = uuid4()
        messages = [
            Message(role=MessageRole.USER, content="hi", conversation_id=conv_id)
        ]
        service.get_conversation_history = AsyncMock(return_value=messages)
        handlers = _make_handlers(service, MagicMock(), _TrackingUnitOfWork())

        result = await handlers.get_messages(
            GetMessagesQuery(conversation_id=conv_id, limit=50)
        )

        assert result == messages
        service.get_conversation_history.assert_awaited_once_with(conv_id, limit=50)


# --- Non-streaming chat orchestration ------------------------------------------
class TestChatHandler:
    """Scenarios: chat routing, source formatting, and the message cap."""

    @pytest.mark.asyncio
    async def test_chat_alter_ego_origin_and_sources(self) -> None:
        conv_id = uuid4()
        conversation = Conversation(id=conv_id, metadata={})
        service = MagicMock()
        service.get_conversation_history = AsyncMock(return_value=[])
        agent = _StubAgent([
            {"type": "complete", "content": "Hello!"},
            {
                "type": "sources",
                "content": [
                    {
                        "document_id": "doc-1",
                        "document_title": "Title",
                        "content": "snippet",
                        "score": 0.9,
                    },
                    "not-a-dict",
                ],
            },
        ])
        agent_factory = MagicMock()
        agent_factory.build_for_conversation.return_value = agent
        handlers = _make_handlers(service, agent_factory, _TrackingUnitOfWork())

        result = await handlers.chat(
            ChatCommand(conversation_id=conv_id, content="Hi"), conversation
        )

        assert result.agent_origin == AGENT_ORIGIN_ALTER_EGO
        assert result.content == "Hello!"
        assert len(result.sources) == 1
        source = result.sources[0]
        assert source.document_id == "doc-1"
        assert source.score == 0.9

    @pytest.mark.asyncio
    async def test_chat_rag_origin_when_project_id_present(self) -> None:
        conv_id = uuid4()
        conversation = Conversation(
            id=conv_id,
            user_id=uuid4(),
            metadata={CONVERSATION_METADATA_PROJECT_ID: "p-1"},
        )
        service = MagicMock()
        service.get_conversation_history = AsyncMock(return_value=[])
        agent_factory = MagicMock()
        agent_factory.build_for_conversation.return_value = _StubAgent([
            {"type": "complete", "content": "Done"}
        ])
        handlers = _make_handlers(service, agent_factory, _TrackingUnitOfWork())

        result = await handlers.chat(
            ChatCommand(conversation_id=conv_id, content="Hi"), conversation
        )

        assert result.agent_origin == AGENT_ORIGIN_RAG
        assert result.content == "Done"

    @pytest.mark.asyncio
    async def test_chat_raises_when_message_cap_reached(self) -> None:
        conv_id = uuid4()
        conversation = Conversation(id=conv_id, metadata={})
        capped = [
            Message(role=MessageRole.USER, content="x", conversation_id=conv_id)
            for _ in range(MAX_MESSAGES_PER_CONVERSATION)
        ]
        service = MagicMock()
        service.get_conversation_history = AsyncMock(return_value=capped)
        agent_factory = MagicMock()
        handlers = _make_handlers(service, agent_factory, _TrackingUnitOfWork())

        with pytest.raises(ConversationLimitReachedError):
            await handlers.chat(
                ChatCommand(conversation_id=conv_id, content="Hi"), conversation
            )

        agent_factory.build_for_conversation.assert_not_called()
