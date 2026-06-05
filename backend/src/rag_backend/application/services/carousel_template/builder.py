"""Carousel template builder facade."""

from rag_backend.application.services.carousel_template.design import (
    generate_design_tokens,
)
from rag_backend.application.services.carousel_template.html_template import (
    build_carousel_html,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_caption_prompt,
    build_content_prompt,
    build_title_prompt,
)


class CarouselTemplateBuilder:
    """Facade for carousel HTML template generation and prompt building."""

    build_title_prompt = staticmethod(build_title_prompt)
    build_content_prompt = staticmethod(build_content_prompt)
    build_caption_prompt = staticmethod(build_caption_prompt)
    build_carousel_html = staticmethod(build_carousel_html)
    generate_design_tokens = staticmethod(generate_design_tokens)


__all__ = ["CarouselTemplateBuilder"]
