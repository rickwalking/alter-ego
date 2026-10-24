"""Versioned cover generation prompt (``agents/prompts/cover_generation/v1/``).

The application service receives the renderer from the API composition edge,
so it imports neither the prompt registry nor the sanitizer. The owner's
direction is sanitised, so it cannot close the template's data markers.
"""

from __future__ import annotations

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.prompts.registry import render_prompt

PROMPT_DOMAIN_COVER_GENERATION = "cover_generation"
PROMPT_COVER_EDIT = "edit"


def cover_edit_prompt(direction: str) -> str:
    """The image instruction sent with the reference photos."""
    prompt, _ = render_prompt(
        PROMPT_DOMAIN_COVER_GENERATION,
        PROMPT_COVER_EDIT,
        {"direction": sanitize_llm_input(direction)},
    )
    return prompt


__all__ = ["cover_edit_prompt"]
