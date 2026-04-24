"""Generate carousel tool for the RAG agent."""

from langchain_core.tools import tool

from rag_backend.domain.models import CarouselProject, CarouselTheme
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository


def build_generate_carousel_tool(
    carousel_agent: CarouselAgent,
    carousel_repository: CarouselRepository,
) -> ...:
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

    return generate_carousel
