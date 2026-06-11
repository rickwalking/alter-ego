"""Blog post workflow observability helpers (OBS-002/003)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from rag_backend.infrastructure.monitoring_langfuse import (
    _TraceConfig,
    create_workflow_trace,
    propagate_attributes,
)

TRACE_UNKNOWN_POST_ID = "unknown"


@dataclass(frozen=True)
class StartupParams:
    """Bundled parameters for starting a blog workflow trace."""

    post_id: str
    user_id: str
    parent_project_id: str | None = None
    carousel_trace_id: str | None = None


def _resolve_trace_project_id(post_id: str) -> UUID:
    """Return a stable UUID for Langfuse grouping."""
    try:
        return UUID(post_id)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"blog-post:{post_id or TRACE_UNKNOWN_POST_ID}")


def start_blog_workflow_trace(params: StartupParams) -> object:
    """Create a blog post workflow trace, optionally linked to a carousel."""
    metadata: dict[str, object] = {"post_id": params.post_id}
    if params.parent_project_id is not None:
        metadata["parent_project_id"] = params.parent_project_id
    if params.carousel_trace_id is not None:
        metadata["carousel_trace_id"] = params.carousel_trace_id
    return create_workflow_trace(
        config=_TraceConfig(
            project_id=_resolve_trace_project_id(params.post_id),
            user_id=params.user_id,
            content_type="blog_post",
            metadata=metadata,
        ),
    )


def blog_ai_propagate(post_id: str, phase: str) -> object:
    """Context manager for grouped blog AI calls."""
    return propagate_attributes(
        metadata={"post_id": post_id, "phase": phase, "content_type": "blog_post"},
    )


__all__ = ["StartupParams", "blog_ai_propagate", "start_blog_workflow_trace"]
