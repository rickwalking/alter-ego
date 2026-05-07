"""LangChain Deep Agent implementation for the Alter-Ego public chat agent.

This agent is intentionally stripped of ALL carousel/content-creation tools.
It can only search the personal knowledge base (Pedro's CV, skills, blog posts)
and answer questions about Pedro Marins' professional identity.
"""

from collections.abc import AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from rag_backend.application.tools.knowledge_base import (
    build_list_documents_tool,
    build_search_documents_tool,
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
from rag_backend.monitoring_langfuse import get_langfuse_handler

_ALTER_EGO_FALLBACK_PROMPT = (
    "You are the Alter-Ego of Pedro Marins, a helpful AI assistant that "
    "represents Pedro's professional identity. You answer questions about "
    "Pedro's career, skills, projects, and published content."
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

            return get_system_prompt("alter_ego", version="v1")
        except Exception:
            return _ALTER_EGO_FALLBACK_PROMPT

    def _build_tools(self) -> list[BaseTool]:
        """Assemble Alter-Ego tools — personal docs ONLY."""
        return [
            build_search_documents_tool(
                self._retriever,
                top_k=5,
                namespace_prefix="personal",
            ),
            build_list_documents_tool(
                self._document_repository,
                scope_filter="personal",
            ),
        ]

    async def chat(  # noqa: C901, PLR0912, PLR0915
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
        history = await self._message_repository.get_by_conversation(conversation_id, limit=10)

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

        sources = []

        if stream:
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

                token = ""
                if isinstance(content, str):
                    token = content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            token += block.get("text", "")
                if not token:
                    continue

                full_response += token
                yield {"type": "token", "content": token}

            if persist_messages:
                assistant_message = Message(
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    conversation_id=conversation_id,
                    sources=sources,
                )
                await self._message_repository.create(assistant_message)

            yield {"type": "sources", "content": sources}
            yield {"type": "complete", "content": full_response}

        else:
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
                    response = msg.content
                    break

            if persist_messages:
                assistant_message = Message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    conversation_id=conversation_id,
                    sources=sources,
                )
                await self._message_repository.create(assistant_message)

            yield {"type": "complete", "content": response}

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for relevant documents (scoped to personal + public)."""
        return await self._retriever.retrieve(
            RetrievalQuery(query=query, top_k=top_k, namespace_prefix="personal")
        )
