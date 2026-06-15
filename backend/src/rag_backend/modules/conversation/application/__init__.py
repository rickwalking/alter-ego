"""Application layer for the conversation bounded context (private to the module).

Holds the use-case entry point (``ConversationService``, reused from its legacy
location) and the ``ChatAgentFactory`` port that abstracts chat-agent
construction. The Unit-of-Work boundary is owned per request/command (ADR-0009
§4). Cross-module consumers use the module facade, not this subpackage.
"""

from rag_backend.modules.conversation.application.agent_factory_port import (
    ChatAgentFactory,
)
from rag_backend.modules.conversation.application.service import ConversationService

__all__ = [
    "ChatAgentFactory",
    "ConversationService",
]
