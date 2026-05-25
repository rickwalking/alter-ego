"""Carousel-related domain models for parameterized interfaces."""

from typing import TypedDict


class ListCarouselsParams(TypedDict):
    """Parameters for listing carousel projects."""

    user: str | None
    status_filter: str | None
    limit: int
    offset: int


class HybridSearchParams(TypedDict):
    """Parameters for hybrid search operations."""

    query: str
    dense_embedding: list[float]
    sparse_embedding: dict[str, list]
    top_k: int
    alpha: float
    namespace: str | None


class ReviewEventParams(TypedDict):
    """Parameters for recording human review events."""

    phase: str
    action: str
    reviewer_id: str
    time_to_respond: str | None
    feedback: str | None
