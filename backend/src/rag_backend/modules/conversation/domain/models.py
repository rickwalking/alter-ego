"""Domain entities and value objects for the conversation bounded context.

Phase 3 is a **behavior-preserving** extraction (ADR-0009; AE-0100). The
conversation aggregate (``Conversation``), its ``Message`` entity, and the
``MessageRole`` value object continue to live at their legacy location
``rag_backend.domain.models.conversation`` so the existing callers (chat routes,
streaming service, ``ConversationService``, the container, agent helpers) keep
importing the exact same objects. This module **re-exports** them under the
module's domain namespace.

Physical relocation of these entities into the module is deferred to a later
phase. Until then ``Conversation`` / ``Message`` are the same class objects as
the legacy ones (re-exports, not wrappers), so identity/isinstance checks and
the existing persistence adapters keep working unchanged.
"""

from __future__ import annotations

from rag_backend.domain.models.conversation import (
    Conversation,
    Message,
    MessageRole,
)

__all__ = [
    "Conversation",
    "Message",
    "MessageRole",
]
