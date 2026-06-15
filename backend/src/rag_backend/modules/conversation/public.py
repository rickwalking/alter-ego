"""Public facade for the conversation bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.conversation.*`` is private to the
module. The dedicated Import Linter facade contract is added alongside the
later phases.

The facade exposes:

* ``ConversationService`` — the use-case entry point (reused from its legacy
  location) with the create/get/history/context/add-message/list/count/title/
  delete operations;
* ``ChatAgentFactory`` — the boundary-safe port for building the chat agent
  bound to a conversation, and ``LegacyChatAgentFactory`` — the concrete adapter
  that wraps the existing builders with identical routing + knowledge-facade
  wiring;
* ``Conversation`` / ``Message`` / ``MessageRole`` — the aggregate, message
  entity, and role value object (re-exported) so existing callers keep a stable
  name during the behavior-preserving phase;
* ``ConversationAdapters`` / ``ConversationModule`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.conversation.application.service`` or
``rag_backend.modules.conversation.domain.models`` directly.
"""

from rag_backend.modules.conversation.application.agent_factory_port import (
    ChatAgentFactory,
)
from rag_backend.modules.conversation.application.commands import (
    ChatCommand,
    ChatResult,
    ChatSource,
    ConversationPage,
    CreateConversationCommand,
    DeleteConversationCommand,
    GenerateTitleCommand,
    GetConversationQuery,
    GetMessagesQuery,
    ListConversationsQuery,
)
from rag_backend.modules.conversation.application.handlers import (
    ConversationHandlers,
    ConversationLimitReachedError,
    LlmGenerate,
)
from rag_backend.modules.conversation.application.service import ConversationService
from rag_backend.modules.conversation.application.streaming import (
    ChatAgentBuilder,
    ConversationStreamHandler,
    StreamChatCommand,
    StreamChatRunner,
)
from rag_backend.modules.conversation.bootstrap import (
    ConversationAdapters,
    ConversationModule,
    bootstrap_module,
)
from rag_backend.modules.conversation.domain.models import (
    Conversation,
    Message,
    MessageRole,
)
from rag_backend.modules.conversation.domain.ports import (
    ConversationRepository,
    MessageRepository,
)
from rag_backend.modules.conversation.infrastructure.chat_agent_factory import (
    LegacyChatAgentFactory,
)
from rag_backend.modules.conversation.infrastructure.stream_runner import (
    LegacyStreamChatRunner,
)

__all__ = [
    "ChatAgentBuilder",
    "ChatAgentFactory",
    "ChatCommand",
    "ChatResult",
    "ChatSource",
    "Conversation",
    "ConversationAdapters",
    "ConversationHandlers",
    "ConversationLimitReachedError",
    "ConversationModule",
    "ConversationPage",
    "ConversationRepository",
    "ConversationService",
    "ConversationStreamHandler",
    "CreateConversationCommand",
    "DeleteConversationCommand",
    "GenerateTitleCommand",
    "GetConversationQuery",
    "GetMessagesQuery",
    "LegacyChatAgentFactory",
    "LegacyStreamChatRunner",
    "ListConversationsQuery",
    "LlmGenerate",
    "Message",
    "MessageRepository",
    "MessageRole",
    "StreamChatCommand",
    "StreamChatRunner",
    "bootstrap_module",
]
