"""The job, collaborators and timings of one blog generation run."""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.application.services.blog.blog_english_gate import (
    EnglishLanguageGate,
)
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
    """Stage budgets and heartbeat cadence (seconds).

    ``text_timeout_seconds`` bounds the writer + both gates + the EN repair;
    the images stage gets ``image_wave_seconds`` per wave of concurrent images.
    """

    text_timeout_seconds: float
    image_wave_seconds: float
    heartbeat_seconds: float


@dataclass(frozen=True)
class BlogGenerationDeps:
    """Collaborators of the run (all behind domain ports)."""

    writer: BlogArticleWriter
    gate: BlogQualityGate
    english: EnglishLanguageGate
    images: BlogImageBatchService
    store: BlogGenerationStore
    timings: GenerationTimings


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
