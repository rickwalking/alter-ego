"""Phases 2-3: content synthesis + slide persistence nodes.

- ``content_node`` drafts bilingual slides via LLM.
- ``persist_slides_node`` idempotently writes slides to the DB.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.content import run_content
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.types import pack_extras
from rag_backend.domain.models import CarouselProject, CarouselSlide, CarouselStatus

NODE_CONTENT = "content"
NODE_PERSIST_SLIDES = "persist_slides"


async def _content_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Optimize title and synthesize bilingual slide content."""
    project: CarouselProject = state["project"]
    project.update_status(CarouselStatus.DRAFTING)
    project = await set_progress(project, repo=deps.repo, label="Drafting bilingual slide content")
    slides_data, blog_markdown = await run_content(
        project, state["sources"], llm=deps.llm, template=deps.template
    )
    return {
        "project": project,
        "slides_data": slides_data,
        "blog_markdown": blog_markdown,
    }


async def _persist_slides_node(state: PipelineState, *, deps: object) -> dict[str, object]:
    """Idempotently persist slides to the DB."""
    project: CarouselProject = state["project"]
    existing_slides = await deps.repo.get_slides_by_project(project.id)
    existing_by_number = {s.slide_number: s for s in existing_slides}

    for sd in state["slides_data"]:
        existing = existing_by_number.get(sd.slide_number)
        if existing:
            updated = CarouselSlide(
                id=existing.id,
                project_id=project.id,
                slide_number=sd.slide_number,
                slide_type=sd.slide_type,
                heading=sd.heading,
                body=sd.body,
                image_prompt=sd.image_prompt,
                extras=pack_extras(sd),
                html_content=existing.html_content,
                image_path=existing.image_path,
                metadata=existing.metadata,
                created_at=existing.created_at,
            )
            await deps.repo.update_slide(updated)
        else:
            slide = CarouselSlide(
                project_id=project.id,
                slide_number=sd.slide_number,
                slide_type=sd.slide_type,
                heading=sd.heading,
                body=sd.body,
                image_prompt=sd.image_prompt,
                extras=pack_extras(sd),
            )
            await deps.repo.create_slide(slide)
    if project.blog_markdown is None:
        project.blog_markdown = state.get("blog_markdown")
    project = await deps.repo.update_project(project)
    return {"project": project}


def build_content_node(deps: object) -> object:
    """Return a closure-bound content node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _content_node(state, deps=deps)

    return node


def build_persist_slides_node(deps: object) -> object:
    """Return a closure-bound persist-slides node."""

    async def node(state: PipelineState) -> dict[str, object]:
        return await _persist_slides_node(state, deps=deps)

    return node
