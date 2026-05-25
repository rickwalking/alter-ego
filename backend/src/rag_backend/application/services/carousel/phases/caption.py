"""Phase 7: Instagram caption generation node."""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.caption import run_caption
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject

NODE_CAPTION = "caption"


async def _caption_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Generate an Instagram caption from slide headings."""
    project: CarouselProject = state["project"]
    caption = await run_caption(
        project, state["slides_data"], llm=deps.llm, template=deps.template
    )
    project.caption = caption
    return {"project": project, "caption": caption}


def build_caption_node(deps: object) -> object:
    """Return a closure-bound caption node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _caption_node(state, deps=deps)

    return node
