"""Phase 6: bilingual export node.

Renders PT slides, then EN slides when translations exist.
"""

from __future__ import annotations

from pathlib import Path

from rag_backend.application.services.carousel.nodes.export import run_bilingual_export
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.domain.models import CarouselProject, CarouselStatus

NODE_EXPORT = "export"


async def _export_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Render PT + EN slide JPGs and PDFs."""
    project: CarouselProject = state["project"]
    project.update_status(CarouselStatus.EXPORTING)
    project = await set_progress(
        project, repo=deps.repo, label="Rendering PT + EN slide HTML to JPG"
    )
    await run_bilingual_export(
        project,
        state["slides_data"],
        state["pt_html"],
        Path(state["output_dir"]),
        export=deps.export,
        pdf_builder=deps.pdf_builder,
        template=deps.template,
    )
    return {"project": project}


def build_export_node(deps: object) -> object:
    """Return a closure-bound export node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _export_node(state, deps=deps)

    return node
