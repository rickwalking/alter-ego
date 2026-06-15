"""Infrastructure layer for the conversation bounded context (private).

Holds the concrete chat-agent factory adapter
(:class:`~rag_backend.modules.conversation.infrastructure.chat_agent_factory.LegacyChatAgentFactory`),
which satisfies the ``ChatAgentFactory`` port by delegating to the existing
agent builders.

**No conversation persistence adapters are relocated in Phase 3 (AE-0100).** The
concrete repositories that implement the conversation ports already exist at
their legacy locations and are imported by other contexts and the container:

* ``rag_backend.infrastructure.database.conversation_repository`` —
  ``PostgresConversationRepository`` / ``PostgresMessageRepository``.

The module's
:func:`~rag_backend.modules.conversation.bootstrap.bootstrap_module` wires the
application service to these existing adapters via manual constructor injection.
Physical relocation into this subpackage is deferred to a later phase.
"""

from rag_backend.modules.conversation.infrastructure.chat_agent_factory import (
    LegacyChatAgentFactory,
)

__all__ = [
    "LegacyChatAgentFactory",
]
