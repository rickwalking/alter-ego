"""Versioned cover generation prompts (``agents/prompts/cover_generation/v1/``).

``edit`` goes with the owner's reference photos; ``generate`` is the
instruction of a cover from the owner's direction alone (no photo).

The application service receives the renderer from the API composition edge,
so it imports neither the prompt registry nor the sanitizer. The owner's
direction is sanitised, so it cannot close the template's data markers.
"""

from __future__ import annotations

from collections.abc import Callable

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.prompts.registry import render_prompt

PROMPT_DOMAIN_COVER_GENERATION = "cover_generation"
PROMPT_COVER_EDIT = "edit"
PROMPT_COVER_GENERATE = "generate"
VARIABLE_DIRECTION = "direction"


def _render(name: str, direction: str) -> str:
    prompt, _ = render_prompt(
        PROMPT_DOMAIN_COVER_GENERATION,
        name,
        {VARIABLE_DIRECTION: sanitize_llm_input(direction)},
    )
    return prompt


def cover_edit_prompt(direction: str) -> str:
    """The image instruction sent with the reference photos."""
    return _render(PROMPT_COVER_EDIT, direction)


def cover_text_prompt(direction: str) -> str:
    """The image instruction of a cover from the direction alone (no photo)."""
    return _render(PROMPT_COVER_GENERATE, direction)


def cover_prompt_for(photo_count: int) -> Callable[[str], str]:
    """The edit instruction when photos go with the job, else the text-only one."""
    return cover_edit_prompt if photo_count else cover_text_prompt


__all__ = ["cover_edit_prompt", "cover_prompt_for", "cover_text_prompt"]
