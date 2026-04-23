"""LangChain Deep Agent implementation for RAG."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from rag_backend.application.services.rag_agent_tools import (
    build_refine_carousel_copy_tool,
    build_refine_carousel_design_tool,
    build_regenerate_slide_image_tool,
)
from rag_backend.domain.models import (
    DocumentStatus,
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
tool to trigger the full 7-phase content generation pipeline.

When a user asks to tweak, shorten, rewrite, or otherwise refine copy on an
existing carousel, call refine_carousel_copy. The UI may prefix the message
with "(carousel project_id=<uuid>)" — extract that UUID and pass it as
project_id. Pick the right target from: instagram_caption, linkedin_post_pt,
linkedin_post_en, slide_heading:N (or slide_heading:N:pt | slide_heading:N:en),
slide_body:N (or slide_body:N:pt | slide_body:N:en). Slide-text edits trigger
an automatic re-export of the slide JPGs and PDF in the language touched. Do
not regenerate the whole carousel for minor edits; refine_carousel_copy is
the correct tool.

When a user asks to change, update, or regenerate an image on a carousel slide,
call regenerate_slide_image with the slide number and a natural-language
instruction describing the desired change. This tool rewrites the image prompt,
generates a new image, and re-exports the slides automatically.

When a user asks to change the layout, sizing, spacing, fonts, or any visual
CSS property of the carousel (e.g., "make the image on slide 3 bigger",
"increase font size", "add more padding"), call refine_carousel_design with
a natural-language instruction. This tool generates CSS overrides, applies
them to the rendered slides, and re-exports without regenerating images.
Do NOT use refine_carousel_copy for layout or sizing changes."""


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
            system_prompt=SYSTEM_PROMPT,
        )

    def _build_tools(self) -> list[Any]:
        # Tools must be plain functions (not bound methods) — LangChain's
        # @tool decorator turns them into StructuredTool instances, and if
        # `self` is a parameter the agent framework injects it a second time
        # at call time ("got multiple values for argument 'self'"). Capture
        # the dependencies via closure instead.
        retriever = self._retriever
        document_repository = self._document_repository
        carousel_agent = self._carousel_agent
        carousel_repository = self._carousel_repository
        llm = self._llm

        @tool
        async def search_documents(query: str) -> str:
            """Search the knowledge base for relevant information.

            Use this tool when you need to find specific information
            from the uploaded documents.

            Args:
                query: The search query string
            """
            results = await retriever.retrieve(RetrievalQuery(query=query, top_k=5))
            if not results:
                return "No relevant documents found."

            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"[{i}] {result.content[:300]}... (Score: {result.score:.3f})"
                )

            return "\n\n".join(formatted_results)

        @tool
        async def list_documents() -> str:
            """List all available documents in the knowledge base.

            Use this to see what information is available.
            """
            docs = await document_repository.get_all(status=DocumentStatus.COMPLETED, limit=20)
            if not docs:
                return "No documents found in the knowledge base."

            formatted_docs = []
            for doc in docs:
                formatted_docs.append(f"- {doc.title} ({doc.chunk_count} chunks)")

            return "Available documents:\n" + "\n".join(formatted_docs)

        tools: list[Any] = [search_documents, list_documents]

        if carousel_agent is None or carousel_repository is None:
            return tools

        @tool
        async def generate_carousel(
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
            from rag_backend.domain.models import CarouselProject, CarouselTheme

            theme_enum = CarouselTheme(theme)
            project = CarouselProject(
                topic=topic,
                audience=audience,
                niche=niche,
                theme=theme_enum,
                language=language,
            )

            created = await carousel_repository.create_project(project)
            result = await carousel_agent.execute_pipeline(created.id, seed_urls=sources)

            slides = await carousel_repository.get_slides_by_project(result.id)
            return (
                f"Carousel generation complete!\n"
                f"Project ID: {result.id}\n"
                f"Status: {result.status.value}\n"
                f"Title: {result.title or topic}\n"
                f"Slides: {len(slides)}\n"
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

        tools.append(generate_carousel)
        tools.append(build_refine_carousel_copy_tool(llm, carousel_repository, carousel_agent))
        tools.append(build_regenerate_slide_image_tool(carousel_agent))
        tools.append(build_refine_carousel_design_tool(carousel_agent))
        return tools

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
        history = await self._message_repository.get_by_conversation(conversation_id, limit=10)

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

            # `astream` in default (values) mode emits nested state chunks
            # like {node_name: {messages: [...]}}, so there is no top-level
            # "messages" key and the old code silently yielded nothing.
            # `astream_events(version="v2")` gives real token deltas via
            # `on_chat_model_stream` events — the LLM's streaming output.
            async for event in self._agent.astream_events(
                {"messages": [*chat_history, HumanMessage(content=message)]},
                version="v2",
            ):
                if event.get("event") != "on_chat_model_stream":
                    continue
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                content = getattr(chunk, "content", None)
                if not content:
                    continue
                # Anthropic streams may deliver content as str OR a list of
                # blocks like [{"type": "text", "text": "..."}, {"type": "tool_use", ...}].
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
        return await self._retriever.retrieve(RetrievalQuery(query=query, top_k=top_k))
