"""Versioned palette prompts (``agents/prompts/palette/v1/``) and their trace.

The application service receives these from the API composition edge, so it
imports neither the prompt registry nor the Langfuse adapter. The owner's
description is sanitised (angle brackets and injection phrases stripped), so it
cannot close the template's data markers.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.prompts.registry import render_prompt
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_USER_ID,
)
from rag_backend.domain.constants.palette_generation import (
    PALETTE_CANDIDATE_COUNT,
    PROMPT_DOMAIN_PALETTE,
    PROMPT_PALETTE_GENERATE,
    TRACE_AGENT_PALETTE_GENERATOR,
    TRACE_CONTENT_TYPE_PALETTE,
    TRACE_PHASE_PALETTE_GENERATION,
)
from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes


def palette_generation_prompt(description: str) -> str:
    """The prompt asking for palette candidates that match ``description``."""
    prompt, _ = render_prompt(
        PROMPT_DOMAIN_PALETTE,
        PROMPT_PALETTE_GENERATE,
        {
            "description": sanitize_llm_input(description),
            "count": PALETTE_CANDIDATE_COUNT,
        },
    )
    return prompt


def palette_generation_trace(user_id: str) -> AbstractContextManager[object]:
    """The Langfuse phase trace of one palette generation for ``user_id``."""
    return propagate_attributes(
        metadata={
            TRACE_FIELD_PHASE: TRACE_PHASE_PALETTE_GENERATION,
            TRACE_FIELD_AGENT_NAME: TRACE_AGENT_PALETTE_GENERATOR,
            TRACE_FIELD_USER_ID: user_id,
            TRACE_FIELD_CONTENT_TYPE: TRACE_CONTENT_TYPE_PALETTE,
        },
    )


__all__ = ["palette_generation_prompt", "palette_generation_trace"]
