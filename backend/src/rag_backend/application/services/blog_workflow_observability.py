"""Blog post workflow observability helpers (OBS-002/003)."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from rag_backend.domain.constants.blog_generation import TRACE_CONTENT_TYPE_BLOG_POST
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_PROJECT_ID,
    TRACE_FIELD_USER_ID,
)
from rag_backend.infrastructure.langfuse_phase_trace import PhaseTrace
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


def blog_ai_propagate(post_id: str, phase: str) -> AbstractContextManager[PhaseTrace]:
    """Context manager for grouped blog AI calls; nested phases reuse the span."""
    return propagate_attributes(
        metadata={"post_id": post_id, "phase": phase, "content_type": "blog_post"},
    )


@dataclass(frozen=True)
class BlogPhaseScope:
    """Langfuse metadata of one blog generation phase (AE-0425)."""

    project_id: str
    user_id: str
    phase: str
    agent_name: str


def blog_phase_trace(
    scope: BlogPhaseScope,
    *,
    input: object | None = None,  # noqa: A002 — Langfuse keyword
) -> AbstractContextManager[PhaseTrace]:
    """Run the enclosed LLM/image calls in the named ``workflow_<phase>`` trace.

    Carries the required metadata (``project_id``, ``phase``, ``agent_name``,
    ``user_id``) with ``content_type="blog_post"`` (AE-0425, AC9). ``input`` is
    the phase brief recorded on the trace/span (AE-0442).
    """
    metadata = {
        TRACE_FIELD_PROJECT_ID: scope.project_id,
        TRACE_FIELD_USER_ID: scope.user_id,
        TRACE_FIELD_PHASE: scope.phase,
        TRACE_FIELD_AGENT_NAME: scope.agent_name,
        TRACE_FIELD_CONTENT_TYPE: TRACE_CONTENT_TYPE_BLOG_POST,
    }
    return propagate_attributes(metadata, input=input)


__all__ = [
    "BlogPhaseScope",
    "StartupParams",
    "blog_ai_propagate",
    "blog_phase_trace",
    "start_blog_workflow_trace",
]
