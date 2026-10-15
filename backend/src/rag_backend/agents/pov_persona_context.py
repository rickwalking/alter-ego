"""The persona block of the "Ponto de Vista" outline (PR #106 review, item 3).

Rendered from the project's persona (``persona_pov/v1/context.yaml``): voice,
signature phrases (the persona's preferred phrases) and forbidden phrases. A
project with no persona gets ``NO_PERSONA_CONTEXT`` explicitly, never a
silently dropped block.
"""

from __future__ import annotations

from rag_backend.agents.input_sanitizer import sanitize_display_input
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.pov_prompts import (
    NO_PERSONA_CONTEXT,
    NO_PHRASES,
    PERSONA_POV_PROMPT_CONTEXT,
    PERSONA_POV_PROMPT_DOMAIN,
    PERSONA_POV_PROMPT_VERSION,
)
from rag_backend.domain.models.persona import PersonaProfile


def _text(value: str | None) -> str:
    """Injection-hardened but case-preserving: phrases are matched verbatim."""
    return sanitize_display_input(value or "")


def _phrases(phrases: list[str]) -> str:
    cleaned = [_text(phrase) for phrase in phrases if phrase.strip()]
    return "; ".join(cleaned) if cleaned else NO_PHRASES


def pov_persona_context(persona: PersonaProfile | None) -> str:
    """The outline's persona block; explicit empty context without a persona."""
    if persona is None:
        return NO_PERSONA_CONTEXT
    text, _model = render_prompt(
        PERSONA_POV_PROMPT_DOMAIN,
        PERSONA_POV_PROMPT_CONTEXT,
        variables={
            "persona_name": _text(persona.name),
            "description": _text(persona.description),
            "opinion_expression": _text(persona.opinion_expression),
            "sentence_structure": _text(persona.sentence_structure_preferences),
            "paragraph_style": _text(persona.paragraph_style),
            "signature_phrases": _phrases(persona.preferred_phrases),
            "forbidden_phrases": _phrases(persona.forbidden_phrases),
        },
        version=PERSONA_POV_PROMPT_VERSION,
    )
    return text.strip()


__all__ = ["pov_persona_context"]
