"""Finalization node.

Marks the project as completed and persists the final state.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject

NODE_FINALIZE = "finalize"


async def _finalize_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Mark project completed and persist."""
    project: CarouselProject = state["project"]
    project.mark_completed(state["output_dir"])
    project = await deps.repo.update_project(project)
    return {"project": project}


def build_finalize_node(deps: object) -> object:
    """Return a closure-bound finalize node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _finalize_node(state, deps=deps)

    return node
