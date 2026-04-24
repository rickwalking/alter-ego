"""Domain-level TypedDicts and type aliases for structured dictionaries.

These replace `dict[str, Any]` usages in protocols and services with
explicit, type-safe shapes.
"""

from __future__ import annotations

from typing import TypedDict


class SparseEmbedding(TypedDict):
    """Pinecone sparse vector format."""

    indices: list[int]
    values: list[float]


class ImageResult(TypedDict):
    """Per-slide image generation outcome."""

    number: int
    status: str
    path: str
    skipped: bool


class PipelineEvent(TypedDict):
    """SSE-shaped event emitted by CarouselAgent.stream_pipeline."""

    node: str
    status: str
    phase_progress: dict[str, object] | None


class ChatEvent(TypedDict, total=False):
    """Event yielded by RAGAgent.chat."""

    type: str
    content: str
    tool: str
    result: str
    sources: list[dict[str, object]]


class StatsResponse(TypedDict):
    """Vector store statistics payload."""

    total_vectors: int
    dimension: int
    index_fullness: float
