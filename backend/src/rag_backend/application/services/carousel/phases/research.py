"""Phase 1: research subgraph node.

Thin wrapper around ``run_research`` that updates project status and
publishes progress before delegating to the pure research function.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.nodes.research import run_research
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

NODE_RESEARCH = "research"


async def _research_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Gather research sources for a carousel project."""
    # Deps is injected as a closure-captured object; we avoid importing
    # CarouselDeps at module level to prevent circular imports with graph.py.
    project: CarouselProject = state["project"]
    project.update_status(CarouselStatus.RESEARCHING)
    project = await deps.repo.update_project(project)
    project = await set_progress(project, repo=deps.repo, label="Searching the web for sources")
    sources = await run_research(
        project,
        state.get("seed_urls", []),
        repo=deps.repo,
        research_tool=deps.research_tool,
    )
    return {"project": project, "sources": sources}


def build_research_node(deps: object) -> object:
    """Return a closure-bound research node for the given deps."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _research_node(state, deps=deps)

    return node
