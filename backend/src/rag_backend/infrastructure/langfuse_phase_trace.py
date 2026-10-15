"""Named Langfuse traces for workflow phases (AE-0390).

Prod 2026-10-15: an autopilot carousel had 10 GLM generations in 3 traces.
Only ``workflow_research`` carried metadata, outline and content generations
had none, one trace had no name, and no trace had tags. The old helper put
the metadata on a span, not on the trace, and the resume path opened no span
at all, so each LLM callback started its own anonymous trace.

``phase_trace`` opens a span named ``workflow_<phase>`` and propagates the
trace attributes (name, user, metadata, tags) to every observation created
inside it, including the LangChain callback generations. Callers that know
the actor but not the phase (the HTTP resume runner, the autopilot driver)
set a ``workflow_trace_scope``; the phase seams read it.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, fields, replace

from langfuse import propagate_attributes as _langfuse_propagate

from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_AGENT_EDITORIAL_WORKFLOW,
    TRACE_CONTENT_TYPE_CAROUSEL,
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_PROJECT_ID,
    TRACE_FIELD_USER_ID,
    TRACE_METADATA_VALUE_MAX_CHARS,
    TRACE_NAME_TEMPLATE,
    TRACE_TAG_AGENT_TEMPLATE,
    TRACE_TAG_CONTENT_TEMPLATE,
    TRACE_TAG_PHASE_TEMPLATE,
    TRACE_VALUE_UNKNOWN,
)
from rag_backend.infrastructure.langfuse_client import get_langfuse_client


@dataclass(frozen=True)
class WorkflowTraceScope:
    """Who runs the workflow. Empty fields inherit from the enclosing scope."""

    project_id: str = ""
    user_id: str = ""
    agent_name: str = ""
    content_type: str = ""


@dataclass(frozen=True)
class PhaseTraceAttributes:
    """The trace name, user, metadata and tags for one phase."""

    name: str
    user_id: str | None
    metadata: dict[str, str]
    tags: tuple[str, ...]


_SCOPE: ContextVar[WorkflowTraceScope | None] = ContextVar(
    "langfuse_workflow_trace_scope",
    default=None,
)


def current_trace_scope() -> WorkflowTraceScope:
    """The scope set by the nearest enclosing ``workflow_trace_scope``."""
    return _SCOPE.get() or WorkflowTraceScope()


@contextmanager
def workflow_trace_scope(scope: WorkflowTraceScope) -> Iterator[None]:
    """Overlay the non-empty fields of ``scope`` for the enclosed calls."""
    token = _SCOPE.set(_overlay(current_trace_scope(), scope))
    try:
        yield
    finally:
        _SCOPE.reset(token)


def build_phase_trace(metadata: Mapping[str, str]) -> PhaseTraceAttributes:
    """Resolve the trace attributes: explicit metadata, then scope, then defaults."""
    scope = _overlay(current_trace_scope(), _scope_of(metadata))
    phase = metadata.get(TRACE_FIELD_PHASE) or TRACE_VALUE_UNKNOWN
    agent = scope.agent_name or TRACE_AGENT_EDITORIAL_WORKFLOW
    content = scope.content_type or TRACE_CONTENT_TYPE_CAROUSEL
    resolved = {
        **{key: str(value) for key, value in metadata.items()},
        TRACE_FIELD_PROJECT_ID: scope.project_id or TRACE_VALUE_UNKNOWN,
        TRACE_FIELD_PHASE: phase,
        TRACE_FIELD_AGENT_NAME: agent,
        TRACE_FIELD_USER_ID: scope.user_id or TRACE_VALUE_UNKNOWN,
        TRACE_FIELD_CONTENT_TYPE: content,
    }
    return PhaseTraceAttributes(
        name=TRACE_NAME_TEMPLATE.format(phase=phase),
        user_id=scope.user_id or None,
        metadata={
            key: value[:TRACE_METADATA_VALUE_MAX_CHARS]
            for key, value in resolved.items()
        },
        tags=(
            TRACE_TAG_PHASE_TEMPLATE.format(value=phase),
            TRACE_TAG_AGENT_TEMPLATE.format(value=agent),
            TRACE_TAG_CONTENT_TEMPLATE.format(value=content),
        ),
    )


@contextmanager
def phase_trace(metadata: Mapping[str, str]) -> Iterator[None]:
    """Run the enclosed LLM calls inside the named, tagged phase trace."""
    client = get_langfuse_client()
    if client is None:
        yield
        return
    attributes = build_phase_trace(metadata)
    try:
        with client.start_as_current_span(
            name=attributes.name, metadata=attributes.metadata
        ) as span:
            span.update_trace(
                name=attributes.name,
                user_id=attributes.user_id,
                metadata=attributes.metadata,
                tags=list(attributes.tags),
            )
            with _propagate(attributes):
                yield
    finally:
        client.flush()


def _propagate(attributes: PhaseTraceAttributes) -> AbstractContextManager[object]:
    return _langfuse_propagate(
        trace_name=attributes.name,
        user_id=attributes.user_id,
        metadata=attributes.metadata,
        tags=list(attributes.tags),
    )


def _scope_of(metadata: Mapping[str, str]) -> WorkflowTraceScope:
    return WorkflowTraceScope(
        project_id=str(metadata.get(TRACE_FIELD_PROJECT_ID) or ""),
        user_id=str(metadata.get(TRACE_FIELD_USER_ID) or ""),
        agent_name=str(metadata.get(TRACE_FIELD_AGENT_NAME) or ""),
        content_type=str(metadata.get(TRACE_FIELD_CONTENT_TYPE) or ""),
    )


def _overlay(base: WorkflowTraceScope, top: WorkflowTraceScope) -> WorkflowTraceScope:
    changes = {
        field.name: getattr(top, field.name)
        for field in fields(top)
        if getattr(top, field.name)
    }
    return replace(base, **changes)


__all__ = [
    "PhaseTraceAttributes",
    "WorkflowTraceScope",
    "build_phase_trace",
    "current_trace_scope",
    "phase_trace",
    "workflow_trace_scope",
]
