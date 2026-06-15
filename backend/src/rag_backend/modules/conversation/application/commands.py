"""Typed command/query objects for the conversation bounded context (AE-0101).

Private to the module — the public facade re-exports the handler entry points;
cross-module code never imports this path directly. These dataclasses carry the
parsed HTTP inputs from the thin route adapter into the conversation handlers so
each handler keeps to a single grouped argument (backend/CLAUDE.md ≤3 args) and
no arbitrary dict bundles cross the boundary.

The objects are framework-free (no FastAPI/SQLAlchemy/Pinecone, no concrete
Postgres repository, no global container): they reference only the module's own
domain types and plain scalars, so the application layer stays a port+facade
consumer (AE-0101 AC).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from rag_backend.modules.conversation.domain.models import Conversation


@dataclass(frozen=True)
class CreateConversationCommand:
    """Create a conversation owned by ``user_id`` (``None`` for anonymous).

    ``metadata`` is passed through to the conversation service unchanged (the
    route forwards the request body's metadata verbatim) so the persisted shape
    and the response stay byte-identical to the legacy path.
    """

    title: str | None
    metadata: dict[str, object]
    user_id: UUID | None


@dataclass(frozen=True)
class ListConversationsQuery:
    """List conversations owned by ``user_id`` with paging + origin filter."""

    user_id: UUID
    limit: int
    offset: int
    origin: str | None


@dataclass(frozen=True)
class GetConversationQuery:
    """Fetch a single conversation by id."""

    conversation_id: UUID


@dataclass(frozen=True)
class GetMessagesQuery:
    """Fetch a conversation's messages, newest-bounded by ``limit``."""

    conversation_id: UUID
    limit: int


@dataclass(frozen=True)
class DeleteConversationCommand:
    """Delete a conversation and all its messages."""

    conversation_id: UUID


@dataclass(frozen=True)
class GenerateTitleCommand:
    """Generate a title for a conversation from its first message."""

    conversation_id: UUID


@dataclass(frozen=True)
class ChatCommand:
    """Send a non-streaming chat message and collect the agent's response."""

    conversation_id: UUID
    content: str


@dataclass(frozen=True)
class ChatSource:
    """A single retrieval source returned alongside a chat response."""

    document_id: str
    document_title: str
    content: str
    score: float


@dataclass(frozen=True)
class ChatResult:
    """The collected non-streaming chat response (content + sources + origin)."""

    content: str
    sources: list[ChatSource] = field(default_factory=list)
    agent_origin: str = ""


@dataclass(frozen=True)
class ConversationPage:
    """A page of conversations plus the matching total for the owner."""

    items: list[Conversation]
    total: int


__all__ = [
    "ChatCommand",
    "ChatResult",
    "ChatSource",
    "ConversationPage",
    "CreateConversationCommand",
    "DeleteConversationCommand",
    "GenerateTitleCommand",
    "GetConversationQuery",
    "GetMessagesQuery",
    "ListConversationsQuery",
]
