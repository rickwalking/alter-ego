"""The persona as prompt *data* for the blog writer (AE-0425, ADR-0025).

Writing samples, phrases and every free-text persona field are untrusted
content: each passes through ``sanitize_llm_input`` (injection phrases and
``< > ( )`` stripped, length capped) before it reaches a prompt, and the
template fences them as data.
"""

from __future__ import annotations

import dataclasses

from rag_backend.agents.blog_writer.constants import (
    MAX_PERSONA_SAMPLE_CHARS,
    MAX_PERSONA_SAMPLES,
    PERSONA_NONE,
)
from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.models.persona import PersonaProfile


def _clean(value: str, limit: int | None = None) -> str:
    cleaned = sanitize_llm_input(value)
    return cleaned[:limit] if limit is not None else cleaned


def _phrases(values: list[str]) -> str:
    cleaned = [_clean(value) for value in values if value.strip()]
    return "; ".join(value for value in cleaned if value) or PERSONA_NONE


def sanitized_persona(persona: PersonaProfile) -> PersonaProfile:
    """A copy whose writing samples are sanitized (for ``PersonaAgent`` scoring)."""
    samples = [
        _clean(sample, MAX_PERSONA_SAMPLE_CHARS)
        for sample in persona.writing_samples[:MAX_PERSONA_SAMPLES]
    ]
    return dataclasses.replace(
        persona, writing_samples=[sample for sample in samples if sample]
    )


def persona_variables(persona: PersonaProfile) -> dict[str, object]:
    """Template variables of the persona (all free text sanitized)."""
    tone = persona.tone_attributes
    return {
        "name": _clean(persona.name),
        "tone_formal": tone.get("formal", 0.5),
        "tone_conversational": tone.get("conversational", 0.5),
        "tone_humorous": tone.get("humorous", 0.5),
        "sentence_structure": _clean(persona.sentence_structure_preferences),
        "paragraph_style": _clean(persona.paragraph_style),
        "opinion_expression": _clean(persona.opinion_expression),
        "expertise_areas": _phrases(persona.expertise_areas),
        "forbidden_phrases": _phrases(persona.forbidden_phrases),
        "preferred_phrases": _phrases(persona.preferred_phrases),
        "writing_samples": sanitized_persona(persona).writing_samples,
    }


__all__ = ["persona_variables", "sanitized_persona"]
