"""Generate carousel tool for the RAG agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langchain_core.tools import BaseTool, tool

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel import validate_theme_reference
from rag_backend.domain.protocols import CarouselRepository

from .access import CarouselToolAccessContext


@dataclass
class SubagentWorkflowStartRequest:
    """Inputs for starting an editorial workflow from the RAG subagent."""

    topic: str
    audience: str
    brief: str
    source_urls: list[str]


WorkflowStartResult = str
# Type alias uses string to avoid circular import via agents.py at module level
# The actual import happens lazily inside build_generate_carousel_tool
WorkflowStarter = Callable[..., Awaitable[WorkflowStartResult]]


def build_generate_carousel_tool(
    carousel_repository: CarouselRepository,
    access: CarouselToolAccessContext,
    *,
    start_editorial_workflow: WorkflowStarter | None = None,
) -> BaseTool:
    """Return the generate_carousel tool closure."""

    @tool
    async def generate_carousel(
        topic: str,
        audience: str,
        niche: str,
        theme: str = "auto",
        language: str = "pt-BR",
        sources: list[str] | None = None,
    ) -> str:
        """Create a carousel project and start the editorial workflow pipeline.

        Use when the user says "create a carousel", "create a social media post",
        "generate carousel slides", or "make an Instagram post".
        """
        validated_theme = validate_theme_reference(theme)
        safe_topic = sanitize_llm_input(topic)
        safe_audience = sanitize_llm_input(audience)
        safe_niche = sanitize_llm_input(niche)
        project = CarouselProject(
            topic=safe_topic,
            audience=safe_audience,
            niche=safe_niche,
            theme=validated_theme,
            language=language,
            owner_id=access.owner_user_id,
        )

        created = await carousel_repository.create_project(project)
        source_urls = sources or []
        if start_editorial_workflow is not None:
            workflow_summary = await start_editorial_workflow(
                str(created.id),
                SubagentWorkflowStartRequest(
                    topic=safe_topic,
                    audience=safe_audience,
                    brief=safe_topic,
                    source_urls=source_urls,
                ),
            )
            return (
                f"Carousel project created and editorial workflow started.\n"
                f"Project ID: {created.id}\n"
                f"{workflow_summary}"
            )
        return (
            f"Carousel project created.\n"
            f"Project ID: {created.id}\n"
            f"Start the editorial workflow via:\n"
            f"  POST /api/carousels/{created.id}/workflow/start"
        )

    return generate_carousel
