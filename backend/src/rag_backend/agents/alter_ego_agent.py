"""LangChain Deep Agent implementation for the Alter-Ego public chat agent.

This agent is intentionally stripped of ALL carousel/content-creation tools.
It can only search the personal knowledge base (Pedro's CV, skills, blog posts)
and answer questions about Pedro Marins' professional identity.
"""

from collections.abc import AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from rag_backend.agents.chat_streaming import extract_message_text, extract_stream_token
from rag_backend.application.tools.knowledge_base import (
    build_list_documents_tool,
    build_search_documents_tool,
)
from rag_backend.domain.constants.namespaces import NAMESPACE_PERSONAL
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
from rag_backend.monitoring_langfuse import get_langfuse_handler

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
    search the personal knowledge base. Anonymous visitors, editors, and
    admins all interact with the same agent for chat — the difference is
    in what routes they can access, not in the agent's toolset.
    """

    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        message_repository: MessageRepository,
        document_repository: DocumentRepository,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._message_repository = message_repository
        self._document_repository = document_repository

        self._llm = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=0.7,
            streaming=True,
        )

        self._agent = create_deep_agent(
            model=self._llm,
            tools=self._build_tools(),
            subagents=[],  # NONE — no delegation to carousel pipeline
            system_prompt=self._load_system_prompt(),
            name="alter-ego-agent",
        )

    def _load_system_prompt(self) -> str:
        """Load Alter-Ego system prompt from registry or fallback."""
        try:
            from rag_backend.agents.prompts.registry import get_system_prompt

            return get_system_prompt("alter_ego", version="v3")
        except Exception:
            return _ALTER_EGO_FALLBACK_PROMPT

    def _build_tools(self) -> list[BaseTool]:
        """Assemble Alter-Ego tools — personal docs ONLY."""
        return [
            build_search_documents_tool(
                self._retriever,
                top_k=10,
                namespace_prefix="personal",
            ),
            build_list_documents_tool(
                self._document_repository,
                scope_filter=NAMESPACE_PERSONAL,
            ),
        ]

    async def chat(
        self,
        message: str,
        conversation_id: UUID,
        *,
        stream: bool = True,
        persist_messages: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        """Process a chat message with optional streaming.

        Mirrors the interface of the legacy RAGAgent so route handlers
        can swap agents without changing their call sites.
        """
        history = await self._message_repository.get_by_conversation(
            conversation_id, limit=10
        )

        chat_history = []
        for msg in history:
            if msg.role == MessageRole.USER:
                chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                chat_history.append(AIMessage(content=msg.content))

        if persist_messages:
            user_message = Message(
                role=MessageRole.USER,
                content=message,
                conversation_id=conversation_id,
            )
            await self._message_repository.create(user_message)

        if stream:
            async for event in self._chat_stream(
                message,
                conversation_id,
                chat_history,
                persist_messages,
            ):
                yield event
        else:
            async for event in self._chat_non_streaming(
                message,
                conversation_id,
                chat_history,
                persist_messages,
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

        Yields tokens as they arrive from the LLM.
        """
        full_response = ""

        callbacks = get_langfuse_handler()
        lf_config: RunnableConfig = {"callbacks": [callbacks]} if callbacks else {}

        async for event in self._agent.astream_events(
            {"messages": [*chat_history, HumanMessage(content=message)]},
            lf_config,
            version="v2",
        ):
            event_name = event.get("event")

            if event_name == "on_tool_end":
                tool_output = event.get("data", {}).get("output")
                tool_name = event.get("name", "")
                if tool_output is not None:
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "result": tool_output,
                    }
                    continue

            if event_name != "on_chat_model_stream":
                continue

            chunk = event.get("data", {}).get("chunk")
            if chunk is None:
                continue
            content = getattr(chunk, "content", None)
            if not content:
                continue

            token = extract_stream_token(content)
            if not token:
                continue

            full_response += token
            yield {"type": "token", "content": token}

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

        messages = result.get("messages", [])
        response = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                response = extract_message_text(msg.content)
                if response:
                    break

        if persist_messages:
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response,
                conversation_id=conversation_id,
            )
            await self._message_repository.create(assistant_message)

        yield {"type": "complete", "content": response}

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for relevant documents (scoped to personal + public)."""
        return await self._retriever.retrieve(
            RetrievalQuery(query=query, top_k=top_k, namespace_prefix="personal")
        )
