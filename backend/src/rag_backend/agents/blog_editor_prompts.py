"""Versioned blog editor prompts (``agents/prompts/blog/v1/``).

Renders the image and section-translation templates. The application services
receive these functions from the API composition edge (they never import the
agents layer), so the prompt text stays in the registry files.
"""

from __future__ import annotations

from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.blog_editor import (
    PROMPT_DOMAIN_BLOG,
    PROMPT_IMAGE,
    PROMPT_TRANSLATE_SECTION,
)


def image_prompt(scene: str) -> str:
    """The provider prompt for an owner-editable image ``scene``."""
    prompt, _ = render_prompt(PROMPT_DOMAIN_BLOG, PROMPT_IMAGE, {"scene": scene})
    return prompt


def translate_section_prompt(heading: str | None, body_md: str) -> str:
    """The PT -> EN translation prompt of one section."""
    prompt, _ = render_prompt(
        PROMPT_DOMAIN_BLOG,
        PROMPT_TRANSLATE_SECTION,
        {"heading": heading or "", "body_md": body_md},
    )
    return prompt


__all__ = ["image_prompt", "translate_section_prompt"]
