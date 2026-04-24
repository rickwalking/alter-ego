"""LangGraph carousel pipeline orchestrator.

``build_graph(deps)`` returns a compiled StateGraph that orchestrates the
8 phases of carousel generation. Node implementations live in
``phases/``; this module only wires edges and compiles the graph.

Dependencies are threaded via a ``CarouselDeps`` dataclass captured by
closure — simpler and more type-safe than stuffing them into
``config["configurable"]``, and the checkpointer only needs to
serialize the ``PipelineState`` channel itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from rag_backend.application.services.carousel.phases import (
    NODE_CAPTION,
    NODE_CONTENT,
    NODE_DESIGN,
    NODE_EXPORT,
    NODE_FINALIZE,
    NODE_IMAGE_WORKER,
    NODE_IMAGES_COLLECT,
    NODE_IMAGES_DISPATCH,
    NODE_LINKEDIN,
    NODE_PERSIST_SLIDES,
    NODE_RESEARCH,
    build_caption_node,
    build_content_node,
    build_design_node,
    build_export_node,
    build_finalize_node,
    build_image_nodes,
    build_linkedin_node,
    build_persist_slides_node,
    build_research_node,
    build_route_after_design,
)
from rag_backend.application.services.carousel.state import PipelineState
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.image_provider_registry import ImageProviderRegistry
from rag_backend.application.services.linkedin_post_generator import LinkedInPostGenerator
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.protocols import (
    CarouselExportService,
    CarouselRepository,
    LLMService,
    ResearchTool,
)

# Retry policies — tuned per node based on what typically fails:
#   - Research: DDG search + Playwright scrapes hit transient 5xx / timeouts.
#   - Content/Caption: LLM provider rate limits and 5xx.
#   - Image worker: vendor API rate limits ($$$ calls; don't retry forever).
# LangGraph records each retry against the same checkpoint, so a crashed
# pipeline resumes with the retry counter intact.
_RETRY_RESEARCH = RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0)
_RETRY_LLM = RetryPolicy(max_attempts=3, initial_interval=2.0, backoff_factor=2.0)
_RETRY_IMAGE = RetryPolicy(max_attempts=2, initial_interval=5.0, backoff_factor=2.0)


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


def build_graph(
    deps: CarouselDeps,
    *,
    checkpointer: BaseCheckpointSaver[object] | None = None,
) -> CompiledStateGraph[PipelineState, object, object, object]:
    """Compile the carousel pipeline into a runnable LangGraph.

    Image generation uses ``Send`` fan-out: one worker task per slide.
    Each worker is an independent graph task, so the checkpointer
    records per-slide progress and a resume only re-runs the slides
    that didn't complete.
    """
    (
        images_dispatch_node,
        image_worker_node,
        images_collect_node,
        dispatch_image_sends,
    ) = build_image_nodes(deps)

    graph = StateGraph(PipelineState)
    graph.add_node(NODE_RESEARCH, build_research_node(deps), retry_policy=_RETRY_RESEARCH)
    graph.add_node(NODE_CONTENT, build_content_node(deps), retry_policy=_RETRY_LLM)
    graph.add_node(NODE_PERSIST_SLIDES, build_persist_slides_node(deps))
    graph.add_node(NODE_DESIGN, build_design_node(deps))
    graph.add_node(NODE_IMAGES_DISPATCH, images_dispatch_node)
    graph.add_node(NODE_IMAGE_WORKER, image_worker_node, retry_policy=_RETRY_IMAGE)
    graph.add_node(NODE_IMAGES_COLLECT, images_collect_node)
    graph.add_node(NODE_EXPORT, build_export_node(deps))
    graph.add_node(NODE_CAPTION, build_caption_node(deps), retry_policy=_RETRY_LLM)
    graph.add_node(NODE_LINKEDIN, build_linkedin_node(deps))
    graph.add_node(NODE_FINALIZE, build_finalize_node(deps))

    graph.add_edge(START, NODE_RESEARCH)
    graph.add_edge(NODE_RESEARCH, NODE_CONTENT)
    graph.add_edge(NODE_CONTENT, NODE_PERSIST_SLIDES)
    graph.add_edge(NODE_PERSIST_SLIDES, NODE_DESIGN)
    graph.add_conditional_edges(
        NODE_DESIGN,
        build_route_after_design,
        [NODE_IMAGES_DISPATCH, NODE_EXPORT],
    )
    graph.add_conditional_edges(
        NODE_IMAGES_DISPATCH,
        dispatch_image_sends,
        [NODE_IMAGE_WORKER],
    )
    graph.add_edge(NODE_IMAGE_WORKER, NODE_IMAGES_COLLECT)
    graph.add_edge(NODE_IMAGES_COLLECT, NODE_EXPORT)
    graph.add_edge(NODE_EXPORT, NODE_CAPTION)
    graph.add_edge(NODE_CAPTION, NODE_LINKEDIN)
    graph.add_edge(NODE_LINKEDIN, NODE_FINALIZE)
    graph.add_edge(NODE_FINALIZE, END)

    return graph.compile(checkpointer=checkpointer)
