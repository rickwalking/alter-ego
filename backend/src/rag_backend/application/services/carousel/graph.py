"""LangGraph carousel pipeline.

`build_graph(deps)` returns a compiled StateGraph that orchestrates the
8 phases currently in `CarouselAgent.execute_pipeline`. Nodes are thin
wrappers around the pure `run_*` functions in `nodes/`, so tests can
still exercise each phase in isolation.

Dependencies (repo, llm, vendor SDKs) are threaded via a `CarouselDeps`
dataclass captured by closure — simpler and more type-safe than
stuffing them into `config["configurable"]`, and the checkpointer only
needs to serialize the `PipelineState` channel itself.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

from rag_backend.application.services.carousel.nodes.caption import run_caption
from rag_backend.application.services.carousel.nodes.content import run_content
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import run_bilingual_export
from rag_backend.application.services.carousel.nodes.images import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_IN_FLIGHT,
    build_initial_status,
    filter_image_slides,
    run_image_one,
)
from rag_backend.application.services.carousel.nodes.linkedin import run_linkedin
from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.carousel.nodes.research import run_research
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel.types import (
    SlideData,
    pack_extras,
    style_display_name,
    unpack_extras,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import ImageProviderRegistry
from rag_backend.application.services.linkedin_post_generator import LinkedInPostGenerator
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.models import CarouselProject, CarouselSlide, CarouselStatus
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    LLMService,
    ResearchTool,
)


class _ImageWorkerState(TypedDict):
    """Per-slide payload for the image fan-out workers."""

    slide: SlideData
    output_dir: str
    worker_index: int
    project: CarouselProject
    all_slides: list[SlideData]


@dataclass
class CarouselDeps:
    """Runtime dependencies captured by closure into each graph node."""

    repo: CarouselRepository
    llm: LLMService
    research_tool: ResearchTool
    image_registry: ImageProviderRegistry
    export: CarouselExportService
    template: CarouselTemplateBuilder
    linkedin_generator: LinkedInPostGenerator | None = None
    pdf_builder: PdfSlideBuilder | None = None


# Retry policies — tuned per node based on what typically fails:
#   - Research: DDG search + Playwright scrapes hit transient 5xx / timeouts.
#   - Content/Caption: LLM provider rate limits and 5xx.
#   - Image worker: vendor API rate limits ($$$ calls; don't retry forever).
# LangGraph records each retry against the same checkpoint, so a crashed
# pipeline resumes with the retry counter intact.
_RETRY_RESEARCH = RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0)
_RETRY_LLM = RetryPolicy(max_attempts=3, initial_interval=2.0, backoff_factor=2.0)
_RETRY_IMAGE = RetryPolicy(max_attempts=2, initial_interval=5.0, backoff_factor=2.0)


# Node name constants — referenced in edges and tests.
NODE_RESEARCH = "research"
NODE_CONTENT = "content"
NODE_PERSIST_SLIDES = "persist_slides"
NODE_DESIGN = "design"
NODE_IMAGES_DISPATCH = "images_dispatch"
NODE_IMAGE_WORKER = "image_worker"
NODE_IMAGES_COLLECT = "images_collect"
NODE_EXPORT = "export"
NODE_CAPTION = "caption"
NODE_LINKEDIN = "linkedin"
NODE_FINALIZE = "finalize"


def build_graph(
    deps: CarouselDeps,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Compile the carousel pipeline into a runnable LangGraph.

    Image generation uses `Send` fan-out: one worker task per slide.
    Each worker is an independent graph task, so the checkpointer
    records per-slide progress and a resume only re-runs the slides
    that didn't complete. The dispatcher publishes an initial pending
    snapshot to the shared progress list; each worker mutates its own
    slot under a closure-scoped lock so the frontend sees live
    per-slide status without cross-worker races.
    """

    # Closure-scoped shared state for Send fan-out progress. Fresh per
    # `build_graph` call, so each pipeline run gets its own isolated
    # tracker — no cross-invocation bleed.
    progress_lock = asyncio.Lock()
    slide_status_box: list[list[dict[str, str | int]]] = [[]]
    style_label_box: list[str] = [""]
    total_box: list[int] = [0]

    async def research_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        project.update_status(CarouselStatus.RESEARCHING)
        project = await deps.repo.update_project(project)
        project = await set_progress(
            project, repo=deps.repo, label="Searching the web for sources"
        )
        sources = await run_research(
            project,
            state.get("seed_urls", []),
            repo=deps.repo,
            research_tool=deps.research_tool,
        )
        return {"project": project, "sources": sources}

    async def content_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        project.update_status(CarouselStatus.DRAFTING)
        project = await set_progress(
            project, repo=deps.repo, label="Drafting bilingual slide content"
        )
        slides_data, blog_markdown = await run_content(
            project, state["sources"], llm=deps.llm, template=deps.template
        )
        return {
            "project": project,
            "slides_data": slides_data,
            "blog_markdown": blog_markdown,
        }

    async def persist_slides_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
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
            project.blog_markdown = state["blog_markdown"]
        project = await deps.repo.update_project(project)
        return {"project": project}

    async def design_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        project.update_status(CarouselStatus.DESIGNING)
        project = await set_progress(
            project, repo=deps.repo, label="Resolving theme and design tokens"
        )
        pt_html = run_design(project, state["slides_data"], template=deps.template)
        project = await deps.repo.update_project(project)
        return {"project": project, "pt_html": pt_html}

    async def _publish_progress(project: CarouselProject) -> CarouselProject:
        """Read-modify-write on `project.phase_progress` under a lock.

        Workers share this via the build_graph closure so concurrent
        Sends don't stomp each other's updates.
        """
        async with progress_lock:
            project.phase_progress = {
                "phase": project.status.value,
                "label": (
                    f"Generating {total_box[0]} slide images in parallel — "
                    f"{style_label_box[0]}"
                ),
                "current": sum(
                    1 for s in slide_status_box[0] if s["status"] == STATUS_DONE
                ),
                "total": total_box[0],
                "slides": [dict(s) for s in slide_status_box[0]],
            }
            return await deps.repo.update_project(project)

    async def images_dispatch_node(state: PipelineState) -> dict[str, Any]:
        """Publish initial per-slide pending snapshot and transition status."""
        project = state["project"]
        project.update_status(CarouselStatus.GENERATING_IMAGES)
        project = await deps.repo.update_project(project)

        slides_with_images = filter_image_slides(state["slides_data"])
        style_label = style_display_name(project.image_model, project.image_style)
        style_label_box[0] = style_label
        total_box[0] = len(slides_with_images)
        slide_status_box[0] = build_initial_status(slides_with_images, style_label)

        project = await _publish_progress(project)
        return {"project": project}

    def _dispatch_image_sends(state: PipelineState) -> list[Send]:
        """Return one Send per slide needing an image (empty list = skip)."""
        project = state["project"]
        slides_with_images = filter_image_slides(state["slides_data"])
        return [
            Send(
                NODE_IMAGE_WORKER,
                _ImageWorkerState(
                    slide=sd,
                    output_dir=state["output_dir"],
                    worker_index=i,
                    project=project,
                    all_slides=slides_with_images,
                ),
            )
            for i, sd in enumerate(slides_with_images)
        ]

    async def image_worker_node(worker_state: _ImageWorkerState) -> dict[str, Any]:
        """Generate one slide image. Writes `image_results` via reducer.

        Idempotency hook: if the target JPG already exists on disk,
        skip the API call. A resumed graph thus only pays for slides
        that were still in-flight when the previous run died.

        Resume safety: `images_dispatch_node` already ran in the first
        session and is skipped on resume, but the closure-scoped
        progress trackers are fresh. The first worker lazily rebuilds
        them from the payload.
        """
        slide = worker_state["slide"]
        index = worker_state["worker_index"]
        output_dir = Path(worker_state["output_dir"])
        project = worker_state["project"]
        image_path = str(output_dir / "images" / f"slide_{slide.slide_number}.jpg")

        # On resume the shared progress list is empty. Rebuild it from
        # the worker payload so indexing works below.
        if not slide_status_box[0]:
            style_label = style_display_name(project.image_model, project.image_style)
            style_label_box[0] = style_label
            # Old checkpoints created before `all_slides` was added to the
            # worker payload may not have the key. Reconstruct from DB.
            all_slides = worker_state.get("all_slides")
            if all_slides is None:
                db_slides = await deps.repo.get_slides_by_project(project.id)
                all_slides = filter_image_slides([unpack_extras(s) for s in db_slides])
            total_box[0] = len(all_slides)
            slide_status_box[0] = build_initial_status(all_slides, style_label)

        if Path(image_path).exists():
            slide_status_box[0][index]["status"] = STATUS_DONE
            return {
                "image_results": [
                    {
                        "number": slide.slide_number,
                        "status": STATUS_DONE,
                        "path": image_path,
                        "skipped": True,
                    }
                ]
            }

        slide_status_box[0][index]["status"] = STATUS_IN_FLIGHT
        await _publish_progress(project)

        try:
            generated_path = await run_image_one(
                project, slide, output_dir, image_registry=deps.image_registry
            )
        except Exception:
            slide_status_box[0][index]["status"] = STATUS_FAILED
            await _publish_progress(project)
            raise

        slide_status_box[0][index]["status"] = STATUS_DONE
        await _publish_progress(project)
        return {
            "image_results": [
                {
                    "number": slide.slide_number,
                    "status": STATUS_DONE,
                    "path": generated_path,
                }
            ]
        }

    async def images_collect_node(state: PipelineState) -> dict[str, Any]:
        """Fan-in: after all workers finish, surface any failures."""
        results = state.get("image_results", [])
        failed = [r for r in results if r.get("status") == STATUS_FAILED]
        if failed:
            raise RuntimeError(
                f"image generation failed for slides: {[r['number'] for r in failed]}"
            )
        return {"project": state["project"]}

    async def export_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
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

    async def caption_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        caption = await run_caption(
            project, state["slides_data"], llm=deps.llm, template=deps.template
        )
        project.caption = caption
        return {"project": project, "caption": caption}

    async def linkedin_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        await run_linkedin(project, repo=deps.repo, generator=deps.linkedin_generator)
        return {"project": project}

    async def finalize_node(state: PipelineState) -> dict[str, Any]:
        project = state["project"]
        project.mark_completed(state["output_dir"])
        project = await deps.repo.update_project(project)
        return {"project": project}

    def _route_after_design(state: PipelineState) -> str:
        """Skip image generation when the project has it disabled."""
        return NODE_IMAGES_DISPATCH if state["project"].generate_images else NODE_EXPORT

    graph = StateGraph(PipelineState)
    graph.add_node(NODE_RESEARCH, research_node, retry_policy=_RETRY_RESEARCH)
    graph.add_node(NODE_CONTENT, content_node, retry_policy=_RETRY_LLM)
    graph.add_node(NODE_PERSIST_SLIDES, persist_slides_node)
    graph.add_node(NODE_DESIGN, design_node)
    graph.add_node(NODE_IMAGES_DISPATCH, images_dispatch_node)
    graph.add_node(NODE_IMAGE_WORKER, image_worker_node, retry_policy=_RETRY_IMAGE)
    graph.add_node(NODE_IMAGES_COLLECT, images_collect_node)
    graph.add_node(NODE_EXPORT, export_node)
    graph.add_node(NODE_CAPTION, caption_node, retry_policy=_RETRY_LLM)
    graph.add_node(NODE_LINKEDIN, linkedin_node)
    graph.add_node(NODE_FINALIZE, finalize_node)

    graph.add_edge(START, NODE_RESEARCH)
    graph.add_edge(NODE_RESEARCH, NODE_CONTENT)
    graph.add_edge(NODE_CONTENT, NODE_PERSIST_SLIDES)
    graph.add_edge(NODE_PERSIST_SLIDES, NODE_DESIGN)
    graph.add_conditional_edges(
        NODE_DESIGN,
        _route_after_design,
        [NODE_IMAGES_DISPATCH, NODE_EXPORT],
    )
    graph.add_conditional_edges(
        NODE_IMAGES_DISPATCH,
        _dispatch_image_sends,
        [NODE_IMAGE_WORKER],
    )
    graph.add_edge(NODE_IMAGE_WORKER, NODE_IMAGES_COLLECT)
    graph.add_edge(NODE_IMAGES_COLLECT, NODE_EXPORT)
    graph.add_edge(NODE_EXPORT, NODE_CAPTION)
    graph.add_edge(NODE_CAPTION, NODE_LINKEDIN)
    graph.add_edge(NODE_LINKEDIN, NODE_FINALIZE)
    graph.add_edge(NODE_FINALIZE, END)

    return graph.compile(checkpointer=checkpointer)
