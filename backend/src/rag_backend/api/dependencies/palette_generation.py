"""Composition edge of "create a palette with AI".

Builds the generation service over the container's fast LLM service (the
``LLM_MODEL_QUEUE_FAST`` queue when configured) and injects the versioned prompt
and its Langfuse trace from the agents layer, so the application service imports
neither. ``api/dependencies`` is the sanctioned container-locator seam.
"""

from __future__ import annotations

from rag_backend.agents.palette_prompts import (
    palette_generation_prompt,
    palette_generation_trace,
)
from rag_backend.api.dependencies.knowledge import get_container
from rag_backend.application.services.carousel.palette_generation_service import (
    PaletteGenerationPorts,
    PaletteGenerationService,
)


def get_palette_generation_service() -> PaletteGenerationService:
    """The palette generator on the fast LLM queue."""
    return PaletteGenerationService(
        PaletteGenerationPorts(
            llm=get_container().fast_llm_service(),
            render_prompt=palette_generation_prompt,
            trace=palette_generation_trace,
        )
    )


__all__ = ["get_palette_generation_service"]
