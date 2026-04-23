"""Phase 7: Instagram caption generation."""

from __future__ import annotations

from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import LLMService

CAPTION_TEMPERATURE = 0.8


async def run_caption(
    project: CarouselProject,
    slides: list[SlideData],
    *,
    llm: LLMService,
    template: CarouselTemplateBuilder,
) -> str:
    """Generate an Instagram caption from the slide headings."""
    slide_headings = [(s.slide_number, s.heading) for s in slides]
    caption_prompt = template.build_caption_prompt(project, slide_headings)
    return await llm.generate(
        messages=[{"role": "user", "content": caption_prompt}],
        temperature=CAPTION_TEMPERATURE,
    )
