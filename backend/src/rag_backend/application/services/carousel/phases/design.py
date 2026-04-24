"""Phase 4: design system node.

Resolves theme, stamps design tokens, and produces the PT HTML string.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject, CarouselStatus

NODE_DESIGN = "design"


async def _design_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Resolve theme and build PT HTML."""
    project: CarouselProject = state["project"]
    project.update_status(CarouselStatus.DESIGNING)
    project = await set_progress(project, repo=deps.repo, label="Resolving theme and design tokens")
    pt_html = run_design(project, state["slides_data"], template=deps.template)
    project = await deps.repo.update_project(project)
    return {"project": project, "pt_html": pt_html}


def build_design_node(deps: object) -> object:
    """Return a closure-bound design node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _design_node(state, deps=deps)

    return node


def build_route_after_design(state: PipelineState) -> str:
    """Skip image generation when the project has it disabled."""
    from rag_backend.application.services.carousel.phases.constants import (
        NODE_EXPORT,
        NODE_IMAGES_DISPATCH,
    )

    return NODE_IMAGES_DISPATCH if state["project"].generate_images else NODE_EXPORT
