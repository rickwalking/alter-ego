"""Domain layer for the conversation bounded context (private to the module).

Exposes the conversation aggregate (``Conversation``), the ``Message`` entity,
the ``MessageRole`` value object, and the two outbound repository ports.
Cross-module consumers do NOT import this subpackage directly — they use the
module facade (``rag_backend.modules.conversation``). This ``__init__`` is an
intra-module convenience for the application/infrastructure/api layers.
"""

from rag_backend.modules.conversation.domain.models import (
    Conversation,
    Message,
    MessageRole,
)
from rag_backend.modules.conversation.domain.ports import (
    ConversationRepository,
    MessageRepository,
)

__all__ = [
    "Conversation",
    "ConversationRepository",
    "Message",
    "MessageRepository",
    "MessageRole",
]
