"""Blog post workflow observability helpers (OBS-002/003)."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from rag_backend.infrastructure.monitoring_langfuse import (
    create_workflow_trace,
    propagate_attributes,
)

TRACE_UNKNOWN_POST_ID = "unknown"


def _resolve_trace_project_id(post_id: str) -> UUID:
    """Return a stable UUID for Langfuse grouping."""
    try:
        return UUID(post_id)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"blog-post:{post_id or TRACE_UNKNOWN_POST_ID}")


def start_blog_workflow_trace(
    post_id: str,
    user_id: str,
    *,
    parent_project_id: str | None = None,
    carousel_trace_id: str | None = None,
) -> object:
    """Create a blog post workflow trace, optionally linked to a carousel."""
    metadata: dict[str, object] = {"post_id": post_id}
    if parent_project_id is not None:
        metadata["parent_project_id"] = parent_project_id
    if carousel_trace_id is not None:
        metadata["carousel_trace_id"] = carousel_trace_id
    return create_workflow_trace(
        project_id=_resolve_trace_project_id(post_id),
        user_id=user_id,
        content_type="blog_post",
        metadata=metadata,
    )


def blog_ai_propagate(post_id: str, phase: str) -> object:
    """Context manager for grouped blog AI calls."""
    return propagate_attributes(
        metadata={"post_id": post_id, "phase": phase, "content_type": "blog_post"},
    )


__all__ = ["blog_ai_propagate", "start_blog_workflow_trace"]
