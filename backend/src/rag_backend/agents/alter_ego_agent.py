"""LangChain Deep Agent implementation for the Alter-Ego public chat agent.

This agent is intentionally stripped of ALL carousel/content-creation tools.
It can only search the knowledge base (Pedro's CV, skills, blog posts) and
answer questions about Pedro Marins' professional identity. What it may read
depends on its ``KnowledgeScope``: public knowledge only for an anonymous
visitor, personal and public knowledge for a signed-in user.
"""

from collections.abc import AsyncIterator
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError

from rag_backend.agents.alter_ego_knowledge import AlterEgoKnowledge
from rag_backend.agents.chat_fallback import no_knowledge_reply
from rag_backend.agents.chat_streaming import (
    chat_event_from_stream,
    is_token_event,
    last_ai_message_text,
)
from rag_backend.agents.harness import (
    AGENT_KIND_CHAT,
    DeepAgentConfig,
    build_deep_agent,
    build_summarization_middleware,
)
from rag_backend.application.services.chat_stream_service import _ChatContext
from rag_backend.application.tools.knowledge_base import (
    SearchToolOptions,
    build_list_documents_tool,
    build_search_documents_tool,
)
from rag_backend.domain.constants.chat_stream import (
    ALTER_EGO_RECURSION_LIMIT,
    ALTER_EGO_SEARCH_BUDGET,
    SSE_EVENT_TOKEN,
)
from rag_backend.domain.constants.retry import LANGGRAPH_MAX_ATTEMPTS
from rag_backend.domain.models import (
    Message,
    MessageRole,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.domain.protocols import (
    DocumentRepository,
    MessageRepository,
    Retriever,
)
from rag_backend.domain.retry import retry_async
from rag_backend.domain.types import ChatEvent
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.knowledge import (
    KnowledgeSearchPort,
    RetrieverSearchAdapter,
)
from rag_backend.monitoring_langfuse import get_langfuse_handler

logger = get_logger()

_ALTER_EGO_FALLBACK_PROMPT = (
    "You are Pedro Marins. Not an AI assistant. Not a chatbot. You.\n\n"
    "You know your own career, your projects, your blog posts, your takes on "
    "tech and leadership. When someone asks you something, you answer like "
    "you're talking to a friend at a coffee shop — direct, honest, sometimes "
    "opinionated.\n\n"
    "You never mention company names, employer names, or client names. "
    "You never answer in bullet points like a resume. You just talk like a person."
)


class AlterEgoAgent:
    """Deep Agent for public-facing Alter-Ego chat.

    Security-critical: this agent has ZERO carousel tools. It can only
    search and list the knowledge base, limited to its knowledge scope:
    anonymous visitors get public knowledge only, signed-in users personal
    and public knowledge.
    """

    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        message_repository: MessageRepository,
        document_repository: DocumentRepository,
        knowledge: AlterEgoKnowledge | None = None,
    ) -> None:
        """Build the chat agent on the shared deep-agent harness.

        Chat agents persist through message_repository only, never a LangGraph
        checkpointer: a second durable write path would dual-write. The harness builder
        routes this chat config through that guard, and the summarization middleware
        caps context-window growth without touching message_repository persistence. No
        subagents are registered: chat never delegates to the carousel pipeline.
        Without ``knowledge`` the agent reads public knowledge only.
        """
        knowledge = knowledge if knowledge is not None else AlterEgoKnowledge()
        self._settings = settings
        self._retriever = retriever
        self._message_repository = message_repository
        self._document_repository = document_repository
        self._scope = knowledge.scope
        self._knowledge_search: KnowledgeSearchPort = (
            knowledge.search
            if knowledge.search is not None
            else RetrieverSearchAdapter(retriever)
        )

        self._llm = build_chat_model(settings)

        self._agent = build_deep_agent(
            DeepAgentConfig(
                model=self._llm,
                name="alter-ego-agent",
                system_prompt=self._load_system_prompt(),
                agent_kind=AGENT_KIND_CHAT,
                tools=self._build_tools(),
                subagents=(),
                middleware=(build_summarization_middleware(self._llm),),
            )
        )

    def _load_system_prompt(self) -> str:
        """Load Alter-Ego system prompt from registry or fallback."""
        try:
            from rag_backend.agents.prompts.registry import get_system_prompt

            return get_system_prompt("alter_ego", version="v3")
        except Exception:
            return _ALTER_EGO_FALLBACK_PROMPT

    def _build_tools(self) -> list[BaseTool]:
        """Assemble Alter-Ego tools, limited to the agent's knowledge scope."""
        return [
            build_search_documents_tool(
                self._knowledge_search,
                SearchToolOptions(
                    top_k=10,
                    namespace_prefix=self._scope.namespace_prefix,
                    max_calls=ALTER_EGO_SEARCH_BUDGET,
                ),
            ),
            build_list_documents_tool(
                self._document_repository,
                scope_filter=self._scope.document_scopes,
            ),
        ]

    async def chat(
        self,
        ctx: _ChatContext,
    ) -> AsyncIterator[ChatEvent]:
        """Process a chat message with optional streaming.

        Mirrors the interface of the legacy RAGAgent so route handlers
        can swap agents without changing their call sites.
        """
        history = await self._message_repository.get_by_conversation(
            ctx.conversation_id, limit=10
        )

        chat_history = []
        for msg in history:
            if msg.role == MessageRole.USER:
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                chat_history.append(AIMessage(content=msg.content))

        if ctx.persist_messages:
            user_message = Message(
                role=MessageRole.USER,
                content=ctx.message,
                conversation_id=ctx.conversation_id,
            )
            await self._message_repository.create(user_message)

        if ctx.stream:
            async for event in self._chat_stream(
                ctx.message,
                ctx.conversation_id,
                chat_history,
                ctx.persist_messages,
            ):
                yield event
        else:
            async for event in self._chat_non_streaming(
                ctx.message,
                ctx.conversation_id,
                chat_history,
                ctx.persist_messages,
            ):
                yield event

    async def _chat_stream(
        self,
        message: str,
        conversation_id: UUID,
        chat_history: list[BaseMessage],
        persist_messages: bool,
    ) -> AsyncIterator[ChatEvent]:
        """Streaming chat implementation.

        Yields tokens as they arrive from the LLM. The agent loop is capped at
        ``ALTER_EGO_RECURSION_LIMIT`` steps; when it runs out before answering
        (for example searching again and again for something the knowledge base
        does not have), the visitor gets an honest "not in my knowledge yet"
        reply instead of an error.
        """
        full_response = ""

        callbacks = get_langfuse_handler()
        lf_config: RunnableConfig = {"recursion_limit": ALTER_EGO_RECURSION_LIMIT}
        if callbacks:
            lf_config["callbacks"] = [callbacks]

        try:
            async for event in self._agent.astream_events(
                {"messages": [*chat_history, HumanMessage(content=message)]},
                lf_config,
                version="v2",
            ):
                chat_event = chat_event_from_stream(event)
                if chat_event is None:
                    continue
                if is_token_event(chat_event):
                    full_response += chat_event.get("content", "")
                yield chat_event
        except GraphRecursionError:
            logger.warning(
                "alter_ego_step_limit_reached",
                conversation_id=str(conversation_id),
                limit=ALTER_EGO_RECURSION_LIMIT,
            )
            fallback = no_knowledge_reply(message)
            if full_response:
                fallback = f"\n\n{fallback}"
            full_response += fallback
            yield {"type": SSE_EVENT_TOKEN, "content": fallback}

        if persist_messages:
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=full_response,
                conversation_id=conversation_id,
            )
            await self._message_repository.create(assistant_message)

        yield {"type": "complete", "content": full_response}

    async def _chat_non_streaming(
        self,
        message: str,
        conversation_id: UUID,
        chat_history: list[BaseMessage],
        persist_messages: bool,
    ) -> AsyncIterator[ChatEvent]:
        """Non-streaming chat implementation.

        Returns complete response at once.
        """
        callbacks = get_langfuse_handler()
        lf_config: RunnableConfig = {"callbacks": [callbacks]} if callbacks else {}
        async for attempt in retry_async(attempts=LANGGRAPH_MAX_ATTEMPTS):
            with attempt:
                result = await self._agent.ainvoke(
                    {"messages": [*chat_history, HumanMessage(content=message)]},
                    lf_config,
                )

        response = last_ai_message_text(result.get("messages", []))

        if persist_messages:
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response,
                conversation_id=conversation_id,
            )
            await self._message_repository.create(assistant_message)

        yield {"type": "complete", "content": response}

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for relevant documents within the agent's knowledge scope."""
        return await self._retriever.retrieve(
            RetrievalQuery(
                query=query,
                top_k=top_k,
                namespace_prefix=self._scope.namespace_prefix,
            )
        )
