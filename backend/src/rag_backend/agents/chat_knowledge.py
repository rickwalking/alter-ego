"""What a chat may read from the knowledge base, by owner and caller.

Personal knowledge is searchable only when the site owner (the user id in
``AUTOPILOT_OWNER_USER_ID``) chats in a conversation the site owner owns. Any
other caller, whether anonymous, an editor or another admin (even one posting
in the site owner's conversation), and the site owner in someone else's
conversation, reads public knowledge only. An unset or unreadable owner id
fails closed to public only, and the public scope is also the default, so a
builder that does not choose never widens what a chat can read.
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
"""Personal and public knowledge, for a conversation of the site owner."""

PUBLIC_KNOWLEDGE = KnowledgeScope(
    namespace_prefix=NAMESPACE_PUBLIC,
    document_scopes=frozenset({NAMESPACE_PUBLIC}),
)
"""Public knowledge only, for every other conversation."""


def _as_uuid(value: object) -> UUID | None:
    """``value`` as a UUID, or ``None`` when missing or not a UUID."""
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return UUID(value.strip())
    except ValueError:
        return None


@dataclass(frozen=True)
class KnowledgeAudience:
    """Who owns the conversation (stored on the server) and who is calling.

    ``None`` stands for an anonymous conversation or an anonymous caller.
    """

    owner_id: UUID | str | None = None
    caller_id: UUID | str | None = None


def knowledge_scope_for(
    audience: KnowledgeAudience, site_owner_id: str
) -> KnowledgeScope:
    """The owner scope only when caller, conversation owner and site owner match.

    ``site_owner_id`` is the configured site owner. Anything else, including an
    empty or invalid ``site_owner_id``, is public.
    """
    site_owner = _as_uuid(site_owner_id)
    owner = _as_uuid(audience.owner_id)
    caller = _as_uuid(audience.caller_id)
    if site_owner is None or owner != site_owner or caller != site_owner:
        return PUBLIC_KNOWLEDGE
    return OWNER_KNOWLEDGE


@dataclass(frozen=True)
class ChatKnowledge:
    """The knowledge search the chat uses and the scope it may read."""

    search: KnowledgeSearchPort | None = None
    scope: KnowledgeScope = PUBLIC_KNOWLEDGE
