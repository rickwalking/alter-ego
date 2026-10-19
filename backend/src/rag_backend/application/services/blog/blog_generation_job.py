"""The job, collaborators and timings of one blog generation run (AE-0425)."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.blog.blog_generated_document import (
    ImageTitles,
)
from rag_backend.application.services.blog.blog_image_batch import (
    BlogImageBatchService,
)
from rag_backend.application.services.blog.blog_quality_gate import BlogQualityGate
from rag_backend.domain.models.blog_generation import (
    GenerationLease,
    GenerationTrace,
    WriterBrief,
)
from rag_backend.domain.protocols.blog_generation import (
    BlogArticleWriter,
    BlogGenerationStore,
)


@dataclass(frozen=True)
class GenerationTimings:
    """Run bound and heartbeat cadence (seconds)."""

    timeout_seconds: float
    heartbeat_seconds: float


@dataclass(frozen=True)
class BlogGenerationDeps:
    """Collaborators of the run (all behind domain ports) + the image cap."""

    writer: BlogArticleWriter
    gate: BlogQualityGate
    images: BlogImageBatchService
    store: BlogGenerationStore
    timings: GenerationTimings
    # BLOG_IMAGE_COST_CAP (AE-0424): images per post, every attempt + the editor.
    image_cap: int


@dataclass(frozen=True)
class GenerationJob:
    """One run: its lease, what to do, and the trace metadata.

    ``brief`` set: the full run (writer → gate → images). ``brief`` is
    ``None``: an images-only retry of an article that already exists — only
    its empty image slots are generated, titled by ``titles``.
    ``retitle`` lets a standalone post take the writer's title.
    """

    lease: GenerationLease
    trace: GenerationTrace
    brief: WriterBrief | None = None
    titles: ImageTitles | None = None
    retitle: bool = False


__all__ = ["BlogGenerationDeps", "GenerationJob", "GenerationTimings"]
