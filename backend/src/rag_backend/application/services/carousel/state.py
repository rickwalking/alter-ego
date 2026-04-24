"""LangGraph state for the carousel pipeline.

Every node reads and writes a subset of these keys. Keys absent on
entry default to None/empty via `total=False`, so nodes can be
registered in any order during graph construction. The `CarouselProject`
object is a full-fat entity that carries its own mutable fields
(status, progress, colors, tokens, blog translations, linkedin posts) —
later phases receive the latest version via this state channel rather
than re-fetching from the repo.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict
from uuid import UUID

from rag_backend.application.services.carousel.types import SlideData
from rag_backend.domain.models import CarouselProject, ResearchSource
from rag_backend.domain.types import ImageResult


class PipelineState(TypedDict, total=False):
    """State flowing between carousel pipeline nodes."""

    # Inputs — set once at graph invocation, never overwritten.
    project_id: UUID
    seed_urls: list[str]
    # Stored as str so checkpointers serialize cleanly; nodes cast with Path().
    output_dir: str

    # Intermediate artifacts, each written by exactly one node.
    project: CarouselProject
    sources: list[ResearchSource]
    slides_data: list[SlideData]
    blog_markdown: str
    pt_html: str
    caption: str

    # Image fan-out: each Send-worker appends one dict
    # `{"number": N, "status": "done"|"failed", "path": "..."}` via the
    # `add` reducer. Lets us see which slides finished vs failed after
    # the fan-in collector node runs.
    image_results: Annotated[list[ImageResult], add]
