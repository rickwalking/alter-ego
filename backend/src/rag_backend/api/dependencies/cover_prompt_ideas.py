"""Composition edge of the cover-photo prompt ideas ("Mais ideias").

Builds the ideas service over the container's fast LLM service (the
``LLM_MODEL_QUEUE_FAST`` queue when configured) with the ideas' token cap and
temperature bound on its chat model, and injects the versioned prompt and its
Langfuse trace from the agents layer. ``api/dependencies`` is the sanctioned
container-locator seam.
"""

from __future__ import annotations

from rag_backend.agents.cover_prompt_prompts import (
    CoverIdeasCompletion,
    cover_ideas_prompt,
    cover_ideas_trace,
)
from rag_backend.api.dependencies.knowledge import get_container
from rag_backend.application.services.carousel.cover_prompt_ideas_service import (
    CoverIdeasPorts,
    CoverPromptIdeasService,
)


def get_cover_prompt_ideas_service() -> CoverPromptIdeasService:
    """The cover-photo idea generator on the fast LLM queue."""
    chat_model = get_container().fast_llm_service().chat_model
    return CoverPromptIdeasService(
        CoverIdeasPorts(
            llm=CoverIdeasCompletion(chat_model),
            render_prompt=cover_ideas_prompt,
            trace=cover_ideas_trace,
        )
    )


__all__ = ["get_cover_prompt_ideas_service"]
