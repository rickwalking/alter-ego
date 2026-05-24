"""LangChain Deep Agent implementation for RAG."""

from collections.abc import AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from rag_backend.application.tools import (
    build_list_documents_tool,
    build_refine_carousel_copy_tool,
    build_refine_carousel_design_tool,
    build_regenerate_slide_image_tool,
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
    CarouselAgent,
    CarouselRepository,
    DocumentRepository,
    MessageRepository,
    Retriever,
)
from rag_backend.domain.retry import retry_async
from rag_backend.domain.types import ChatEvent
from rag_backend.infrastructure.config.settings import Settings
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
        carousel_agent: CarouselAgent | None = None,
        carousel_repository: CarouselRepository | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._message_repository = message_repository
        self._document_repository = document_repository
        self._carousel_agent = carousel_agent
        self._carousel_repository = carousel_repository

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
            skills=["skills/carousel-pipeline"],
            name="rag-agent",
        )

    def _build_subagents(self) -> list[dict[str, object]]:
        """Return DeepAgents-compatible subagent specs.

        The carousel pipeline is exposed as a subagent so the parent RAG
        agent can delegate complex multi-step carousel work via the
        ``task`` tool instead of cluttering the top-level toolset.
        """
        if self._carousel_agent is None:
            return []
        return [self._carousel_agent.to_subagent(self._settings.carousel_output_dir)]

    def _build_tools(self) -> list[BaseTool]:
        """Assemble agent tools from domain-specific builders.

        Each tool is created by a factory that captures the runtime
        dependencies via closure. This keeps the agent class focused
        on orchestration while tools live in their own domain modules.
        """
        tools: list[BaseTool] = [
            build_search_documents_tool(self._retriever, top_k=5),
            build_list_documents_tool(self._document_repository),
        ]

        if self._carousel_agent is None or self._carousel_repository is None:
            return tools

        from rag_backend.application.tools.carousel.generate_carousel import (
            build_generate_carousel_tool,
        )

        tools.extend(
            [
                build_generate_carousel_tool(self._carousel_agent, self._carousel_repository),
                build_refine_carousel_copy_tool(
                    self._llm, self._carousel_repository, self._carousel_agent
                ),
                build_regenerate_slide_image_tool(self._carousel_agent),
                build_refine_carousel_design_tool(self._carousel_agent),
            ]
        )
        return tools

    async def chat(  # noqa: C901,PLR0912,PLR0915 — streaming + non-streaming paths
        self,
        message: str,
        conversation_id: UUID,
        *,
        stream: bool = True,
        persist_messages: bool = True,
    ) -> AsyncIterator[ChatEvent]:
        """Process a chat message with optional streaming.

        Args:
            message: The user's message
            conversation_id: The conversation ID
            stream: Whether to stream the response
            persist_messages: Whether to persist user/assistant messages to
                the message repository. Set to False when the caller handles
                persistence (e.g. WebSocket handler) to avoid session-flush
                conflicts with tool side-effects.

        Yields:
            Dictionary with 'type' and content:
            - type='token': Token text chunk
            - type='tool_result': A tool finished (name + raw output)
            - type='sources': List of source documents
            - type='complete': Final complete message
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
                # Anthropic streams may deliver content as str OR a list of
                # blocks like [{"type": "text", "text": "..."}, {"type": "tool_use", ...}].
                token = ""  # nosec B105 — string accumulator, not a password
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
                    raw = msg.content
                    if isinstance(raw, str):
                        response = raw
                    elif isinstance(raw, list):
                        for block in raw:
                            if isinstance(block, dict) and block.get("type") == "text":
                                response += block.get("text", "")
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
