"""LangFuse observability integration for full workflow visibility."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, TypedDict, cast
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langfuse import Langfuse

from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.infrastructure.langfuse_client import (
    get_langfuse_client,
)

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


class _TraceConfig(TypedDict, total=False):
    """Bundled configuration for creating a trace or child trace."""

    parent_trace_id: str
    """Parent trace ID for child traces (create_child_trace)."""
    name: str
    """Trace name."""
    project_id: UUID
    """Project UUID (create_workflow_trace)."""
    user_id: str
    """User identifier (create_workflow_trace)."""
    content_type: str
    """Content type label (create_workflow_trace)."""
    metadata: dict[str, object] | None
    """Extra metadata attached to the trace."""
    tags: list[str] | None
    """Optional tags for the trace."""


class _ScoreParams(TypedDict, total=False):
    """Bundled parameters for add_quality_score."""

    criterion: str
    """Score criterion name."""
    score: float
    """Score value (0-100)."""
    threshold: float
    """Minimum passing threshold."""
    passed: bool
    """Whether the criterion passed."""


class _ErrorParams(TypedDict, total=False):
    """Bundled parameters for add_error_span."""

    error_type: str
    """Type of error."""
    error_message: str
    """Error message."""
    retry_count: int
    """Number of retries attempted."""
    fallback_used: bool
    """Whether fallback was used."""


class LangfuseCallbackHandler:
    """LangChain callback handler that traces everything to LangFuse.

    Traces:
    - Every LLM call with tokens, latency, model
    - Human interrupts with timing
    - Tool calls with inputs/outputs
    - Errors with retry count
    - Quality scores as LangFuse Score objects
    """

    def __init__(self, langfuse_client: Langfuse) -> None:
        """Initialize the callback handler.

        Args:
            langfuse_client: LangFuse client instance
        """
        self.client = langfuse_client
        self._current_trace: object = None
        self._current_span: object = None
        self._run_stack: list[object] = []

    def on_text(self, run: object) -> None:
        """Handle text generation runs."""
        self._create_span(run, "generation")

    def on_chat_model_start(
        self, run: object, _serialized: dict[str, object], _inputs: dict[str, object]
    ) -> None:
        """Handle LLM call starts."""
        self._create_span(run, "llm_call")

    def on_chat_model_end(self, run: object) -> None:
        """Handle LLM call ends."""
        if (
            self._current_span
            and self._current_span.name == "llm_call"  # type: ignore[attr-defined]
            and run.execution_time  # type: ignore[attr-defined]
        ):
            self._current_span.update(  # type: ignore[attr-defined]
                {"latency": run.execution_time, "status": "completed"}  # type: ignore[attr-defined]
            )

    def on_tool_start(self, run: object) -> None:
        """Handle tool call starts."""
        self._create_span(run, "tool_call")

    def on_tool_end(self, run: object) -> None:
        """Handle tool call ends."""
        if self._current_span:
            self._current_span.update(  # type: ignore[attr-defined]
                {
                    "status": "completed",
                    "output": run.output,  # type: ignore[attr-defined]
                    "latency": run.execution_time,  # type: ignore[attr-defined]
                }
            )

    def on_error(self, run: object, error: Exception) -> None:
        """Handle errors."""
        if self._current_span:
            self._current_span.update(  # type: ignore[attr-defined]
                {
                    "status": "failed",
                    "error": str(error),
                    "retry_count": getattr(run, "iteration", 0),
                }
            )

    def _create_span(self, run: object, span_type: str) -> None:
        """Create or update a LangFuse span."""
        if self._run_stack and self._run_stack[-1] == run:
            self._run_stack.pop()

        trace_name = f"{span_type}_{run.name}"  # type: ignore[attr-defined]
        tags = run.tags or []  # type: ignore[attr-defined]

        if self._current_trace is None:
            self._current_trace = self.client.trace(  # type: ignore[attr-defined]
                name=trace_name,
                tags=tags,
                metadata={"run_id": run.id},  # type: ignore[attr-defined]
            )

        span = self._current_trace.span(  # type: ignore[attr-defined]
            name=f"{span_type}: {run.name}",  # type: ignore[attr-defined]
            metadata={
                "run_id": run.id,  # type: ignore[attr-defined]
                "run_type": run.run_type,  # type: ignore[attr-defined]
                "inputs": run.inputs,  # type: ignore[attr-defined]
            },
        )

        self._current_span = span
        self._run_stack.append(run)

    def set_tags(self, tags: list[str]) -> None:
        """Set tags on current trace."""
        if self._current_trace:
            self._current_trace.update(tags=tags)  # type: ignore[attr-defined]

    def set_metadata(self, metadata: dict[str, object]) -> None:
        """Set metadata on current trace."""
        if self._current_trace:
            self._current_trace.update(metadata=metadata)  # type: ignore[attr-defined]

    def add_score(
        self,
        name: str,
        score: float,
        observation: dict[str, object],
    ) -> None:
        """Add a LangFuse score to the trace.

        Args:
            name: Score name (e.g., "quality", "voice_match")
            score: Score value (0-1)
            observation: Additional observation data
        """
        if self._current_trace:
            self._current_trace.score(  # type: ignore[attr-defined]
                name=name,
                score=score,
                observation=observation,
                comment=f"Score: {score:.2f}",
            )

    def create_child_trace(
        self,
        *,
        config: _TraceConfig,
    ) -> object:
        """Create a child trace linked to parent.

        Used for cross-trace visibility (e.g., blog post from carousel).

        Args:
            config: Bundled trace configuration (parent_trace_id, name, …).

        Returns:
            Child trace object
        """
        parent_trace_id = config["parent_trace_id"]
        name = config["name"]
        metadata = config.get("metadata")
        tags = config.get("tags")
        return self.client.trace(  # type: ignore[attr-defined]
            name=name,
            metadata={
                "parent_trace_id": parent_trace_id,
                "relationship": "derived_from",
                **(metadata or {}),
            },
            tags=tags or [],
        )


def get_langfuse_handler() -> list[BaseCallbackHandler]:
    """Get LangChain-compatible Langfuse callbacks when configured."""
    from rag_backend.monitoring_langfuse import get_langfuse_handler as get_root_handler

    handler = get_root_handler()
    if handler is None:
        return []
    return [cast(BaseCallbackHandler, handler)]


def get_langfuse_runnable_config() -> "RunnableConfig":
    """Return LangChain RunnableConfig with Langfuse callbacks when available."""
    handlers = get_langfuse_handler()
    if not handlers:
        return {}
    return {"callbacks": handlers}


@contextmanager
def propagate_attributes(
    metadata: dict[str, str],
    callbacks: list[object] | None = None,
) -> Generator[None, None, None]:
    """Propagate metadata across multiple LLM calls via Langfuse v3 spans."""
    _ = callbacks
    client = get_langfuse_client()

    if client is None:
        yield
        return

    span = client.start_as_current_span(
        name=f"workflow_{metadata.get('phase', 'unknown')}",
        metadata=metadata,
    )
    try:
        with span:
            yield
    finally:
        client.flush()


def create_workflow_trace(
    *,
    config: _TraceConfig,
) -> object:
    """Create a trace span for a workflow using Langfuse v3 SDK."""
    client = get_langfuse_client()

    if client is None:
        return None

    project_id = config["project_id"]
    user_id = config["user_id"]
    content_type = config["content_type"]
    metadata = config.get("metadata")

    return client.start_span(
        name=f"{content_type}_workflow_{project_id}",
        metadata={
            "project_id": str(project_id),
            "user_id": user_id,
            "content_type": content_type,
            "tags": [content_type, "workflow"],
            **(metadata or {}),
        },
    )


def add_quality_score(
    trace: object,
    *,
    params: _ScoreParams,
) -> None:
    """Add a quality score to a trace.

    Args:
        trace: LangFuse trace object
        params: Bundled score parameters (criterion, score, threshold, passed).
    """
    if trace is None:
        return
    criterion = params["criterion"]
    score = params["score"]
    threshold = params["threshold"]
    passed = params.get("passed", False)
    normalized_score = score / 100.0

    trace.score(  # type: ignore[attr-defined]
        name=f"quality_{criterion}",
        score=normalized_score,
        observation={
            "score": score,
            "threshold": threshold,
            "passed": passed,
        },
    )


def add_voice_match_score(
    trace: object,
    score: float,
    suggestions: list[str] | None = None,
) -> None:
    """Add voice match score to a trace.

    Args:
        trace: LangFuse trace object
        score: Voice match score (0-100)
        suggestions: Optional improvement suggestions
    """
    if trace is None:
        return

    normalized_score = score / 100.0

    trace.score(  # type: ignore[attr-defined]
        name="voice_match",
        score=normalized_score,
        observation={
            "score": score,
            "suggestions": suggestions or [],
        },
    )


def record_human_review(trace: object, *, params: ReviewEventParams) -> None:
    """Record a human review event.

    Args:
        trace: LangFuse trace object
        params: Review event metadata
    """
    if trace is None:
        return

    if hasattr(trace, "create_event"):
        trace.create_event(
            name=f"human_review_{params['phase']}_completed",
            metadata=params,
        )
        return

    trace.event(  # type: ignore[attr-defined]
        name=f"human_review_{params['phase']}_completed",
        metadata=params,
    )


def add_error_span(
    trace: object,
    *,
    params: _ErrorParams,
) -> None:
    """Add an error span to a trace.

    Args:
        trace: LangFuse trace object
        params: Bundled error parameters (error_type, error_message, …).
    """
    if trace is None:
        return

    error_type = params["error_type"]
    error_message = params["error_message"]
    retry_count = params.get("retry_count", 0)
    fallback_used = params.get("fallback_used", False)

    trace.span(  # type: ignore[attr-defined]
        name=f"error_{error_type}",
        metadata={
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "fallback_used": fallback_used,
        },
        input={},
        output={"error": error_message},
    )


__all__ = [
    "LangfuseCallbackHandler",
    "add_error_span",
    "add_quality_score",
    "add_voice_match_score",
    "create_workflow_trace",
    "get_langfuse_handler",
    "get_langfuse_runnable_config",
    "propagate_attributes",
]
