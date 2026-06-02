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
from rag_backend.application.services.carousel_template.slides import (
    _render_content_slide,
    _render_cta_slide,
    _render_intro_slide,
    _render_summary_slide,
)


class CarouselTemplateBuilder:
    build_title_prompt = staticmethod(build_title_prompt)
    build_content_prompt = staticmethod(build_content_prompt)
    build_caption_prompt = staticmethod(build_caption_prompt)
    build_carousel_html = staticmethod(build_carousel_html)
    generate_design_tokens = staticmethod(generate_design_tokens)
    _render_intro_slide = staticmethod(_render_intro_slide)
    _render_summary_slide = staticmethod(_render_summary_slide)
    _render_content_slide = staticmethod(_render_content_slide)
    _render_cta_slide = staticmethod(_render_cta_slide)


__all__ = ["CarouselTemplateBuilder"]
