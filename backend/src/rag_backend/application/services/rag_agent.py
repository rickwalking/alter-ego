"""LangChain Deep Agent implementation for RAG."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from rag_backend.domain.models import DocumentStatus, Message, MessageRole, SearchResult
from rag_backend.domain.protocols import (
    CarouselAgent,
    DocumentRepository,
    MessageRepository,
    Retriever,
)
from rag_backend.infrastructure.config.settings import Settings

SYSTEM_PROMPT = """You are a helpful AI assistant with access to a knowledge base.

When answering questions:
1. First, search the knowledge base using the search_documents tool
2. Use the retrieved information to provide accurate, contextual answers
3. Cite your sources when providing information from documents
4. If you don't find relevant information, say so clearly
5. Always be helpful, accurate, and concise

You can also create Instagram carousels and blog content. When a user asks to
create a carousel, social media post, or blog content, use the generate_carousel
tool to trigger the full 7-phase content generation pipeline."""


class RAGAgent:
    """Deep Agent-based RAG agent with tools."""

    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        message_repository: MessageRepository,
        document_repository: DocumentRepository,
        carousel_agent: CarouselAgent | None = None,
    ) -> None:
        self._settings = settings
        self._retriever = retriever
        self._message_repository = message_repository
        self._document_repository = document_repository
        self._carousel_agent = carousel_agent

        self._llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.7,
            streaming=True,
        )

        agent_tools = [self._search_documents_tool, self._list_documents_tool]
        if self._carousel_agent is not None:
            agent_tools.append(self._generate_carousel_tool)

        self._agent = create_deep_agent(
            model=self._llm,
            tools=agent_tools,
            system_prompt=SYSTEM_PROMPT,
        )

    @tool
    async def _search_documents_tool(self, query: str) -> str:
        """Search the knowledge base for relevant information.

        Use this tool when you need to find specific information
        from the uploaded documents.

        Args:
            query: The search query string
        """
        results = await self._retriever.retrieve(query, top_k=5)
        if not results:
            return "No relevant documents found."

        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"[{i}] {result.content[:300]}... (Score: {result.score:.3f})"
            )

        return "\n\n".join(formatted_results)

    @tool
    async def _list_documents_tool(self) -> str:
        """List all available documents in the knowledge base.

        Use this to see what information is available.
        """
        docs = await self._document_repository.get_all(
            status=DocumentStatus.COMPLETED, limit=20
        )
        if not docs:
            return "No documents found in the knowledge base."

        formatted_docs = []
        for doc in docs:
            formatted_docs.append(f"- {doc.title} ({doc.chunk_count} chunks)")

        return "Available documents:\n" + "\n".join(formatted_docs)

    @tool
    async def _generate_carousel_tool(
        self,
        topic: str,
        audience: str,
        niche: str,
        theme: str = "auto",
        language: str = "pt-BR",
        sources: list[str] | None = None,
    ) -> str:
        """Generate an Instagram carousel and blog post with full 7-phase pipeline.

        Creates research-backed carousel slides, bilingual blog content (pt-BR + en),
        visual design tokens, images, and an Instagram caption.

        Use when the user says "create a carousel", "create a social media post",
        "generate carousel slides", or "make an Instagram post".

        Args:
            topic: The main topic for the carousel content
            audience: Target audience (e.g., "software developers, AI engineers")
            niche: Content niche (e.g., "AI/Tech", "Cybersecurity")
            theme: Visual theme. Options: cybersecurity, ai_competition,
                   developer_skills, source_code, social_engineering, auto
            language: Primary language (default: pt-BR for Brazilian Portuguese)
            sources: Optional list of source URLs to research
        """
        if self._carousel_agent is None:
            return "Carousel generation is not available. Please configure the carousel agent."

        from rag_backend.domain.models import CarouselProject, CarouselTheme

        theme_enum = CarouselTheme(theme)
        project = CarouselProject(
            topic=topic,
            audience=audience,
            niche=niche,
            theme=theme_enum,
            language=language,
        )

        from rag_backend.infrastructure.container import get_container

        container = get_container()
        repo = container.carousel_repository()

        created = await repo.create_project(project)
        result = await self._carousel_agent.execute_pipeline(created.id)

        status_info = (
            f"Carousel generation complete!\n"
            f"Project ID: {result.id}\n"
            f"Status: {result.status.value}\n"
            f"Title: {result.title or topic}\n"
            f"Slides: {len(await repo.get_slides_by_project(result.id))}\n"
            f"Blog available: {'Yes' if result.blog_markdown else 'No'}\n"
            f"Caption available: {'Yes' if result.caption else 'No'}\n"
            f"Design tokens: {'Yes' if result.design_tokens else 'No'}\n\n"
            f"Access the carousel content via:\n"
            f"  GET /api/carousels/{result.id}/blog (default pt-BR)\n"
            f"  GET /api/carousels/{result.id}/blog/pt\n"
            f"  GET /api/carousels/{result.id}/blog/en\n"
            f"  GET /api/carousels/{result.id}/design\n"
            f"  GET /api/carousels/{result.id}/slides"
        )
        return status_info

    async def chat(
        self, message: str, conversation_id: UUID, stream: bool = True
    ) -> AsyncIterator[dict[str, Any]]:
        """Process a chat message with optional streaming.

        Args:
            message: The user's message
            conversation_id: The conversation ID
            stream: Whether to stream the response

        Yields:
            Dictionary with 'type' and content:
            - type='token': Token text chunk
            - type='sources': List of source documents
            - type='complete': Final complete message
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

        user_message = Message(
            role=MessageRole.USER,
            content=message,
            conversation_id=conversation_id,
        )
        await self._message_repository.create(user_message)

        sources = []

        if stream:
            full_response = ""

            async for chunk in self._agent.astream(
                {"messages": [*chat_history, HumanMessage(content=message)]}
            ):
                if isinstance(chunk, dict) and "messages" in chunk:
                    for msg in chunk["messages"]:
                        if isinstance(msg, AIMessage) and msg.content:
                            token = msg.content
                            full_response += token
                            yield {"type": "token", "content": token}

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
            result = await self._agent.ainvoke(
                {"messages": [*chat_history, HumanMessage(content=message)]}
            )

            messages = result.get("messages", [])
            response = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response = msg.content
                    break

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
        return await self._retriever.retrieve(query, top_k=top_k)
