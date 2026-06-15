"""Application service (use case entry point) for the conversation module.

Private to the module — the public facade re-exports it under
``ConversationService``; cross-module code never imports this path directly.

**Reuse, not rewrite (AE-0100 constraint).** The conversation use cases already
live in ``rag_backend.application.services.conversation_service`` and are wired
into the chat routes and the streaming service today. Phase 3 is
behavior-preserving (ADR-0009): this module **re-exports** that existing service
so the facade exposes the conversation operations (create/get/history/context/
add-message/list/count/title/delete) without duplicating or relocating logic.

Dependencies are injected through the constructor (manual constructor injection,
ADR-0009 §9): the request-scoped ``ConversationRepository`` and
``MessageRepository`` are built at the inbound (api) edge and passed in by
``bootstrap_module``; this service does not resolve a global container.
"""

from __future__ import annotations

from rag_backend.application.services.conversation_service import ConversationService

__all__ = [
    "ConversationService",
]
