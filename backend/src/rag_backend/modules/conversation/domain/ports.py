"""Outbound ports (Protocols) for the conversation bounded context.

The conversation ports are:

* ``ConversationRepository`` — conversation persistence;
* ``MessageRepository`` — message persistence.

**Re-export, not relocation (AE-0100 constraint).** These Protocols are defined
in the SHARED protocol file ``rag_backend.domain.protocols.repositories`` which
is imported by ~50+ non-conversation callers (the chat routes, the streaming
service, ``ConversationService``, the container, agent helpers). Physically
moving the definitions would break those imports, so this phase keeps the
definitions where they are and merely **re-exports** them here. The legacy
import paths (``rag_backend.domain.protocols.repositories.ConversationRepository``
etc.) keep resolving to the IDENTICAL Protocol objects, while the module domain
layer also exposes them as its own ports. Per backend/CLAUDE.md, interfaces are
``typing.Protocol``, never ABCs.

This mirrors ``modules.knowledge.domain.ports`` exactly (object-identity shim).
"""

from __future__ import annotations

from rag_backend.domain.protocols.repositories import (
    ConversationRepository,
    MessageRepository,
)

__all__ = [
    "ConversationRepository",
    "MessageRepository",
]
