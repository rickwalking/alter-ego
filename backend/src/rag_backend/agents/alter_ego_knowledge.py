"""What the Alter-Ego chat may read from the knowledge base, by audience.

An anonymous visitor's chat reads the owner's public knowledge only; the chat
of a signed-in user (the owner's dashboard chat) reads personal and public
knowledge. The public scope is the default, so a builder that does not choose
never widens what the chat can read.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.constants.namespaces import (
    NAMESPACE_PERSONAL,
    NAMESPACE_PUBLIC,
)
from rag_backend.modules.knowledge import KnowledgeSearchPort


@dataclass(frozen=True)
class KnowledgeScope:
    """The namespace prefix the chat searches and the document scopes it lists.

    The retriever resolves the ``personal`` prefix to the ``personal`` and
    ``public`` namespaces, and the ``public`` prefix to ``public`` alone.
    """

    namespace_prefix: str
    document_scopes: frozenset[str]


OWNER_KNOWLEDGE = KnowledgeScope(
    namespace_prefix=NAMESPACE_PERSONAL,
    document_scopes=frozenset({NAMESPACE_PERSONAL, NAMESPACE_PUBLIC}),
)
"""Personal and public knowledge, for a signed-in user's conversation."""

PUBLIC_KNOWLEDGE = KnowledgeScope(
    namespace_prefix=NAMESPACE_PUBLIC,
    document_scopes=frozenset({NAMESPACE_PUBLIC}),
)
"""Public knowledge only, for an anonymous visitor's conversation."""


def knowledge_scope_for(owner_id: UUID | None) -> KnowledgeScope:
    """The public scope for an anonymous conversation, else the owner scope."""
    if owner_id is None:
        return PUBLIC_KNOWLEDGE
    return OWNER_KNOWLEDGE


@dataclass(frozen=True)
class AlterEgoKnowledge:
    """The knowledge search the chat uses and the scope it may read."""

    search: KnowledgeSearchPort | None = None
    scope: KnowledgeScope = PUBLIC_KNOWLEDGE
