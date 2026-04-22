"""LangChain Deep Agent implementation for RAG."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
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
the correct tool."""


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

        @tool
        async def refine_carousel_copy(
            project_id: str,
            target: str,
            instruction: str,
        ) -> str:
            """Rewrite a specific piece of copy on an existing carousel project.

            Use when the user asks to tweak the Instagram caption, LinkedIn
            post (PT or EN), a slide heading, or a slide body on a carousel
            they already generated.

            Args:
                project_id: UUID of the carousel project to edit.
                target: Which field to rewrite. One of:
                    - "instagram_caption"
                    - "linkedin_post_pt"
                    - "linkedin_post_en"
                    - "slide_heading:N" or "slide_heading:N:pt|en"
                    - "slide_body:N" or "slide_body:N:pt|en"
                    Bare slide_heading:N / slide_body:N defaults to PT.
                instruction: Natural-language edit request from the user
                    (e.g. "make it shorter", "swap the hashtags for tech ones",
                    "less corporate").
            """
            from uuid import UUID as _UUID

            try:
                project_uuid = _UUID(project_id)
            except ValueError:
                return f"Invalid project_id {project_id!r} — expected a UUID."

            project = await carousel_repository.get_project_by_id(project_uuid)
            if project is None:
                return f"Carousel project {project_id} not found."

            original, apply_update = await _resolve_refine_target(
                project, target, carousel_repository
            )
            if original is None:
                return f"Cannot refine {target!r}: field is empty or target selector is unknown."

            rewrite_prompt = (
                "You are editing existing social copy. Apply the user's "
                "instruction verbatim to the text below. Return ONLY the "
                "rewritten text, nothing else.\n\n"
                f"Instruction: {instruction}\n\n"
                f"Original text:\n<<<\n{original}\n>>>"
            )
            response = await llm.ainvoke(rewrite_prompt)
            new_text = str(getattr(response, "content", response) or "").strip()
            if not new_text:
                return "LLM returned empty text; no changes applied."

            await apply_update(new_text)

            # When the edit touches a slide's text, re-render the slide
            # JPGs + PDF so the user-visible artifacts match the DB.
            # Caption + LinkedIn edits skip this — they live in tabs.
            re_render_note = ""
            if target.startswith("slide_"):
                try:
                    await carousel_agent.re_render_slides(project_uuid)  # type: ignore[attr-defined]
                    re_render_note = " Slides + PDF re-rendered."
                except (ValueError, AttributeError) as exc:
                    re_render_note = f" Re-render skipped: {exc}"

            return (
                f"Updated {target} on project {project_id}. "
                f"New length: {len(new_text)} chars.{re_render_note}"
            )

        tools.append(refine_carousel_copy)
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


async def _resolve_refine_target(
    project: CarouselProject,
    target: str,
    repository: CarouselRepository,
) -> tuple[str | None, Callable[[str], Awaitable[None]]]:
    """Return (current_text, async_setter) for the refine target.

    Keeps the branching out of the tool closure so the set of supported
    targets is easy to extend without bloating the tool function.
    """
    if target == "instagram_caption":

        async def _set_caption(new_text: str) -> None:
            project.caption = new_text
            await repository.update_project(project)

        return project.caption, _set_caption

    if target == "linkedin_post_pt":

        async def _set_pt(new_text: str) -> None:
            project.linkedin_post_pt = new_text
            await repository.update_project(project)

        return project.linkedin_post_pt, _set_pt

    if target == "linkedin_post_en":

        async def _set_en(new_text: str) -> None:
            project.linkedin_post_en = new_text
            await repository.update_project(project)

        return project.linkedin_post_en, _set_en

    async def _noop(_: str) -> None:
        return None

    if target.startswith("slide_heading:") or target.startswith("slide_body:"):
        # Selectors:
        #   slide_heading:N            (PT, default — backward compat)
        #   slide_body:N
        #   slide_heading:N:pt | slide_heading:N:en
        #   slide_body:N:pt    | slide_body:N:en
        parts = target.split(":")
        field = parts[0]
        if len(parts) < 2:
            return None, _noop
        try:
            slide_number = int(parts[1])
        except ValueError:
            return None, _noop
        language = parts[2] if len(parts) >= 3 else "pt"
        if language not in {"pt", "en"}:
            return None, _noop

        slides = await repository.get_slides_by_project(project.id)
        slide = next((s for s in slides if s.slide_number == slide_number), None)
        if slide is None:
            return None, _noop

        current = _read_slide_field(slide, field, language)

        async def _update_slide(new_text: str) -> None:
            _write_slide_field(slide, field, language, new_text)
            await repository.update_slide(slide)

        return current, _update_slide

    return None, _noop


def _read_slide_field(slide: CarouselSlide, field: str, language: str) -> str:
    """Read heading/body for the requested language, falling back to PT."""
    if language == "en":
        translation = (slide.extras or {}).get("translation_en") if slide.extras else None
        if isinstance(translation, dict):
            value = translation.get("heading" if field == "slide_heading" else "body")
            if isinstance(value, str) and value:
                return value
    return slide.heading if field == "slide_heading" else slide.body


def _write_slide_field(slide: CarouselSlide, field: str, language: str, new_text: str) -> None:
    """Mutate heading/body in place for the target language."""
    if language == "en":
        extras: dict[str, object] = dict(slide.extras or {})
        translation = extras.get("translation_en")
        if not isinstance(translation, dict):
            translation = {}
        translation = dict(translation)
        translation["heading" if field == "slide_heading" else "body"] = new_text
        extras["translation_en"] = translation
        slide.extras = extras
        return
    if field == "slide_heading":
        slide.heading = new_text
    else:
        slide.body = new_text
