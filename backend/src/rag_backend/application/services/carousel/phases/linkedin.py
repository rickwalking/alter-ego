"""Phase 8: LinkedIn post generation node.

No-op when the LinkedIn generator is not wired.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.linkedin import run_linkedin
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject

NODE_LINKEDIN = "linkedin"


async def _linkedin_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Generate bilingual LinkedIn posts."""
    project: CarouselProject = state["project"]
    await run_linkedin(project, repo=deps.repo, generator=deps.linkedin_generator)
    return {"project": project}


def build_linkedin_node(deps: object) -> object:
    """Return a closure-bound LinkedIn node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _linkedin_node(state, deps=deps)

    return node
