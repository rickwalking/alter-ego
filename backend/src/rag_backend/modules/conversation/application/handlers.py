"""Command/query handlers for the conversation bounded context (AE-0101).

Private to the module — the public facade re-exports the handler class;
cross-module code never imports this path directly. The handlers are the
use-case entry points the thin ``/api/conversations`` route adapter delegates to:
each maps a typed command/query (``application.commands``) onto the conversation
``ConversationService`` facade and, for chat, the ``ChatAgentFactory`` port.

Behavior-preserving (AE-0101): every handler reproduces the legacy route's data
operations exactly (same service calls, same agent-origin routing, same message
cap). HTTP concerns — status codes, access checks (``resource_access`` /
``carousel_access``), cookies, and the ``X-Agent-Origin`` header — stay in the
route adapter, mirroring how ``documents.py`` keeps access checks at the edge.

The application layer imports only ports, the facade service, other application
services, and domain types — never a concrete Postgres repository or the global
container (AE-0101 AC). Writes are committed by the route through the platform
Unit of Work (the single committer); these handlers never call ``commit()``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.application.services.chat_stream_service import _ChatContext
from rag_backend.application.services.conversation_service import (
    ConversationService,
    _ListQuery,
)
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.modules.conversation.application.agent_factory_port import (
    ChatAgentFactory,
)
from rag_backend.modules.conversation.application.commands import (
    ChatCommand,
    ChatResult,
    ChatSource,
    ConversationPage,
    CreateConversationCommand,
    DeleteConversationCommand,
    GenerateTitleCommand,
    GetConversationQuery,
    GetMessagesQuery,
    ListConversationsQuery,
)
from rag_backend.modules.conversation.domain.models import Conversation, Message
from rag_backend.platform.database import UnitOfWork

# Agent-origin header values + non-stream chat event types (mirrors the legacy
# ``conversations.py`` route constants byte-for-byte).
AGENT_ORIGIN_ALTER_EGO = "alter-ego"
AGENT_ORIGIN_RAG = "rag-agent"
MAX_MESSAGES_PER_CONVERSATION = 20

_EVENT_TYPE_COMPLETE = "complete"
_EVENT_TYPE_SOURCES = "sources"

_SOURCE_DOCUMENT_ID_KEY = "document_id"
_SOURCE_DOCUMENT_TITLE_KEY = "document_title"
_SOURCE_CONTENT_KEY = "content"
_SOURCE_SCORE_KEY = "score"

# Async callable that generates text from the LLM (matches ``LLMService.generate``
# and the ``ConversationService.generate_title`` parameter contract).
LlmGenerate = Callable[[list[dict[str, str]]], Awaitable[str]]


class ConversationLimitReachedError(Exception):
    """Raised when a conversation has reached its message cap (route maps 429)."""


class ConversationHandlers:
    """Use-case handlers wrapping the conversation facade + agent-factory port.

    Constructed per request by the inbound edge from the bootstrapped
    ``ConversationModule`` (the ``ConversationService`` facade and the bound
    ``ChatAgentFactory``). Holds no framework state and resolves no global
    container.
    """

    def __init__(
        self,
        service: ConversationService,
        agent_factory: ChatAgentFactory,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._service = service
        self._agent_factory = agent_factory
        self._unit_of_work = unit_of_work

    async def create(self, command: CreateConversationCommand) -> Conversation:
        """Create a conversation, committed once via the UoW (single committer).

        The route sets the anon cookie afterwards from the returned conversation
        id; the id is assigned client-side at construction, so it is available
        immediately after the committed create (byte-identical to the legacy
        create-then-commit-then-cookie order).
        """
        async with self._unit_of_work:
            return await self._service.create_conversation(
                title=command.title,
                metadata=command.metadata,
                user_id=command.user_id,
            )

    async def list_for_owner(self, query: ListConversationsQuery) -> ConversationPage:
        """List the owner's conversations plus the matching total."""
        conversations = await self._service.list_conversations(
            query=_ListQuery(
                limit=query.limit,
                offset=query.offset,
                user_id=query.user_id,
                origin=query.origin,
            ),
        )
        total = await self._service.count_conversations_for_user(
            query.user_id, origin=query.origin
        )
        return ConversationPage(items=conversations, total=total)

    async def get(self, query: GetConversationQuery) -> Conversation | None:
        """Fetch a single conversation, or ``None`` if absent (route maps 404)."""
        return await self._service.get_conversation(query.conversation_id)

    async def get_messages(self, query: GetMessagesQuery) -> list[Message]:
        """Fetch a conversation's messages (route checks access first)."""
        return await self._service.get_conversation_history(
            query.conversation_id, limit=query.limit
        )

    async def delete(self, command: DeleteConversationCommand) -> bool:
        """Delete a conversation, committed once via the UoW (route 404 if False).

        The route resolves + access-checks the conversation first (preserving the
        404/403 order); this handler performs the delete inside the UoW so the
        platform UoW is the single committer (the route never calls ``commit()``).
        """
        async with self._unit_of_work:
            return await self._service.delete_conversation(command.conversation_id)

    async def generate_title(
        self,
        command: GenerateTitleCommand,
        llm_generate: LlmGenerate,
    ) -> Conversation | None:
        """Generate + persist a title via the UoW, returning the refreshed row."""
        async with self._unit_of_work:
            await self._service.generate_title(
                conversation_id=command.conversation_id,
                llm_generate_func=llm_generate,
            )
        return await self._service.get_conversation(command.conversation_id)

    async def chat(
        self,
        command: ChatCommand,
        conversation: Conversation,
    ) -> ChatResult:
        """Run the non-streaming chat turn for an already-loaded conversation.

        The route resolves + access-checks ``conversation`` (preserving the exact
        403/404 semantics) and passes it in; this handler enforces the message
        cap, builds the agent via the factory port, drains the non-streaming
        events, and returns the collected content/sources plus the agent-origin
        the route writes to the ``X-Agent-Origin`` header.
        """
        await self._assert_under_message_cap(command.conversation_id)
        agent = self._agent_factory.build_for_conversation(conversation)
        agent_origin = (
            AGENT_ORIGIN_RAG
            if CONVERSATION_METADATA_PROJECT_ID in conversation.metadata
            else AGENT_ORIGIN_ALTER_EGO
        )
        content, sources = await self._drain_chat_events(agent, command)
        return ChatResult(
            content=content,
            sources=sources,
            agent_origin=agent_origin,
        )

    async def _assert_under_message_cap(self, conversation_id: UUID) -> None:
        history = await self._service.get_conversation_history(
            conversation_id,
            limit=MAX_MESSAGES_PER_CONVERSATION,
        )
        if len(history) >= MAX_MESSAGES_PER_CONVERSATION:
            raise ConversationLimitReachedError

    @staticmethod
    async def _drain_chat_events(
        agent: AlterEgoAgent | RAGAgent,
        command: ChatCommand,
    ) -> tuple[str, list[ChatSource]]:
        full_response = ""
        sources: list[ChatSource] = []
        async for event in agent.chat(
            _ChatContext(
                message=command.content,
                conversation_id=command.conversation_id,
                stream=False,
            ),
        ):
            if event["type"] == _EVENT_TYPE_COMPLETE:
                full_response = str(event["content"])
            elif event["type"] == _EVENT_TYPE_SOURCES:
                sources = _format_sources(event["content"])
        return full_response, sources


def _format_sources(raw: object) -> list[ChatSource]:
    """Map the agent's ``sources`` event payload to typed ``ChatSource`` items.

    Mirrors the legacy route's coercion exactly: only ``dict`` entries are kept
    and each scalar is coerced with the same defaults (empty string / ``0.0``).
    """
    if not isinstance(raw, list):
        return []
    return [
        ChatSource(
            document_id=str(src.get(_SOURCE_DOCUMENT_ID_KEY, "")),
            document_title=str(src.get(_SOURCE_DOCUMENT_TITLE_KEY, "")),
            content=str(src.get(_SOURCE_CONTENT_KEY, "")),
            score=float(src.get(_SOURCE_SCORE_KEY, 0.0)),
        )
        for src in raw
        if isinstance(src, dict)
    ]


__all__ = [
    "AGENT_ORIGIN_ALTER_EGO",
    "AGENT_ORIGIN_RAG",
    "MAX_MESSAGES_PER_CONVERSATION",
    "ConversationHandlers",
    "ConversationLimitReachedError",
    "LlmGenerate",
]
