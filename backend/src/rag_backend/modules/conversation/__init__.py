"""Conversation bounded context (Supporting) — AE-0100 Phase 3 skeleton.

The conversation context owns conversation/message persistence, the chat
use cases, and chat-agent construction. This package follows the module
conventions (``docs/architecture/module-conventions.md``, AE-0081) and ADR-0009
(Domain Modular Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here);
* manual constructor injection via ``bootstrap_module`` (ADR-0009 §9);
* the Unit-of-Work boundary owned at the application layer.

Phase 3 is **behavior-preserving** (AE-0100): the ``Conversation`` / ``Message``
entities and the ``ConversationRepository`` / ``MessageRepository`` ports are
*re-exported* from their legacy locations (no physical move, object-identity
shims), ``ConversationService`` is reused as-is, the ``ChatAgentFactory`` adapter
delegates to the existing builders (identical routing + knowledge-facade wiring),
and no routes/streaming move. Routes move behind this facade in AE-0101/0102.

Cross-module consumers SHALL import from the facade only, e.g.::

    from rag_backend.modules.conversation import ConversationService, ChatAgentFactory
"""

from rag_backend.modules.conversation.public import (
    ChatAgentFactory,
    Conversation,
    ConversationAdapters,
    ConversationModule,
    ConversationRepository,
    ConversationService,
    LegacyChatAgentFactory,
    Message,
    MessageRepository,
    MessageRole,
    bootstrap_module,
)

__all__ = [
    "ChatAgentFactory",
    "Conversation",
    "ConversationAdapters",
    "ConversationModule",
    "ConversationRepository",
    "ConversationService",
    "LegacyChatAgentFactory",
    "Message",
    "MessageRepository",
    "MessageRole",
    "bootstrap_module",
]
