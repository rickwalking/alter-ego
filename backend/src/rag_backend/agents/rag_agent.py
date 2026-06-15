"""LangChain Deep Agent implementation for RAG."""

from collections.abc import AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from rag_backend.agents.chat_streaming import extract_message_text, extract_stream_token
from rag_backend.application.services.chat_stream_service import _ChatContext
from rag_backend.application.tools import (
    build_list_documents_tool,
    build_refine_carousel_copy_tool,
    build_refine_carousel_design_tool,
    build_regenerate_slide_image_tool,
    build_search_documents_tool,
)
from rag_backend.application.tools.carousel.access import CarouselToolAccessContext
from rag_backend.domain.constants.retry import LANGGRAPH_MAX_ATTEMPTS
from rag_backend.domain.models import (
    Message,
    MessageRole,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.domain.protocols import (
    CarouselRefinementService,
    CarouselRepository,
    DocumentRepository,
    MessageRepository,
    Retriever,
)
from rag_backend.domain.retry import retry_async
from rag_backend.domain.types import ChatEvent
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.knowledge import (
    KnowledgeSearchPort,
    RetrieverSearchAdapter,
)
from rag_backend.monitoring_langfuse import get_langfuse_handler


def _load_system_prompt() -> str:
    """Load RAG system prompt from external registry.

    Falls back to inline constant if registry is unavailable.
    """
    try:
        from rag_backend.agents.prompts.registry import get_system_prompt

        return get_system_prompt("rag", version="v1")
    except Exception:
        return _FALLBACK_SYSTEM_PROMPT


_FALLBACK_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Prompt registry unavailable — load agents/prompts/rag/v1/system.md"
)


class RAGAgent:
    """Deep Agent-based RAG agent with tools."""

    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        message_repository: MessageRepository,
        document_repository: DocumentRepository,
        carousel_refinement: CarouselRefinementService | None = None,
        carousel_repository: CarouselRepository | None = None,
        editorial_subagent: dict[str, object] | None = None,
        start_editorial_workflow: object | None = None,
        carousel_tool_access: CarouselToolAccessContext | None = None,
        knowledge_search: KnowledgeSearchPort | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._message_repository = message_repository
        self._document_repository = document_repository
        self._carousel_refinement = carousel_refinement
        self._carousel_repository = carousel_repository
        self._editorial_subagent = editorial_subagent
        self._start_editorial_workflow = start_editorial_workflow
        self._carousel_tool_access = carousel_tool_access
        self._knowledge_search: KnowledgeSearchPort = (
            knowledge_search
            if knowledge_search is not None
            else RetrieverSearchAdapter(retriever)
        )

        self._llm = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=0.7,
            streaming=True,
        )

        self._agent = create_deep_agent(
            model=self._llm,
            tools=self._build_tools(),
            subagents=self._build_subagents(),
            system_prompt=_load_system_prompt(),
            name="rag-agent",
        )

    def _build_subagents(self) -> list[dict[str, object]]:
        """Return DeepAgents-compatible subagent specs."""
        if self._editorial_subagent is None:
            return []
        return [self._editorial_subagent]

    def _build_tools(self) -> list[BaseTool]:
        """Assemble agent tools from domain-specific builders.

        Each tool is created by a factory that captures the runtime
        dependencies via closure. This keeps the agent class focused
        on orchestration while tools live in their own domain modules.
        """
        tools: list[BaseTool] = [
            build_search_documents_tool(self._knowledge_search, top_k=5),
            build_list_documents_tool(self._document_repository),
        ]

        if self._carousel_refinement is None or self._carousel_repository is None:
            return tools
        if self._carousel_tool_access is None:
            return tools

        from rag_backend.application.tools.carousel.generate_carousel import (
            build_generate_carousel_tool,
        )

        tools.extend([
            build_generate_carousel_tool(
                self._carousel_repository,
                self._carousel_tool_access,
                start_editorial_workflow=self._start_editorial_workflow,
            ),
            build_refine_carousel_copy_tool(
                self._llm,
                self._carousel_repository,
                self._carousel_refinement,
                self._carousel_tool_access,
            ),
            build_regenerate_slide_image_tool(
                self._carousel_refinement,
                self._carousel_repository,
                self._carousel_tool_access,
            ),
            build_refine_carousel_design_tool(
                self._carousel_refinement,
                self._carousel_repository,
                self._carousel_tool_access,
            ),
        ])
        return tools

    async def chat(
        self,
        ctx: _ChatContext,
    ) -> AsyncIterator[ChatEvent]:
        """Process a chat message with optional streaming.

        Args:
            ctx: Chat context with message, conversation_id, stream, and
                persist_messages settings.

        Yields:
            Dictionary with 'type' and content:
            - type='token': Token text chunk
            - type='error': Error message
            - type='tool_result': A tool finished (name + raw output)
            - type='sources': List of source documents
            - type='complete': Final complete message
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

        sources = []

        if ctx.stream:
            async for event in self._chat_stream(
                ctx.message,
                ctx.conversation_id,
                chat_history,
                sources,
                ctx.persist_messages,
            ):
                yield event
        else:
            async for event in self._chat_non_streaming(
                ctx.message,
                ctx.conversation_id,
                chat_history,
                sources,
                ctx.persist_messages,
            ):
                yield event

    async def _chat_stream(
        self,
        message: str,
        conversation_id: UUID,
        chat_history: list[HumanMessage | AIMessage],
        sources: list[dict[str, object]],
        persist_messages: bool,
    ) -> AsyncIterator[ChatEvent]:
        """Streaming chat implementation."""
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
                sources=sources,
            )
            await self._message_repository.create(assistant_message)

        yield {"type": "sources", "content": sources}
        yield {"type": "complete", "content": full_response}

    async def _chat_non_streaming(
        self,
        message: str,
        conversation_id: UUID,
        chat_history: list[HumanMessage | AIMessage],
        sources: list[dict[str, object]],
        persist_messages: bool,
    ) -> AsyncIterator[ChatEvent]:
        """Non-streaming chat implementation."""
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
                sources=sources,
            )
            await self._message_repository.create(assistant_message)

        yield {"type": "complete", "content": response}

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for relevant documents."""
        return await self._retriever.retrieve(RetrievalQuery(query=query, top_k=top_k))
