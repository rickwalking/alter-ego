"""Named Langfuse traces for workflow phases (AE-0390, AE-0442).

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

AE-0442: Langfuse v3 derives trace I/O from the root observation. The phase
must therefore put the brief and the result on the span/trace itself, and a
nested phase must reuse the outer span instead of opening a second one whose
``unknown`` metadata overwrites the actor. ``generation_run_name`` lets call
sites name generations after the phase and the unit of work (``slide 3``)
instead of the model class (``ChatOpenAI``).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, fields, replace
from typing import Protocol, cast

from langfuse import propagate_attributes as _langfuse_propagate

from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_AGENT_EDITORIAL_WORKFLOW,
    TRACE_CONTENT_TYPE_CAROUSEL,
    TRACE_DEFAULT_RUN_NAME,
    TRACE_ERROR_FIELD_MESSAGE,
    TRACE_ERROR_FIELD_TYPE,
    TRACE_FIELD_AGENT_NAME,
    TRACE_FIELD_CONTENT_TYPE,
    TRACE_FIELD_PHASE,
    TRACE_FIELD_PROJECT_ID,
    TRACE_FIELD_USER_ID,
    TRACE_IO_VALUE_MAX_CHARS,
    TRACE_METADATA_VALUE_MAX_CHARS,
    TRACE_NAME_TEMPLATE,
    TRACE_OUTPUT_STATUS_COMPLETED,
    TRACE_OUTPUT_STATUS_ERROR,
    TRACE_RUN_NAME_SEPARATOR,
    TRACE_STATUS_FIELD,
    TRACE_TAG_AGENT_TEMPLATE,
    TRACE_TAG_CONTENT_TEMPLATE,
    TRACE_TAG_PHASE_TEMPLATE,
    TRACE_VALUE_UNKNOWN,
)
from rag_backend.infrastructure.langfuse_client import get_langfuse_client
from rag_backend.infrastructure.logging import redact_secrets


class TraceSpan(Protocol):
    """The subset of a Langfuse span the phase trace uses."""

    def update_trace(  # noqa: PLR0913 — mirrors the Langfuse SDK signature
        self,
        *,
        name: str | None = ...,
        user_id: str | None = ...,
        session_id: str | None = ...,
        input: object | None = ...,  # noqa: A002 — Langfuse keyword
        output: object | None = ...,
        metadata: Mapping[str, str] | None = ...,
        tags: list[str] | None = ...,
    ) -> object: ...

    def update(  # noqa: PLR0913 — mirrors the Langfuse SDK signature
        self,
        *,
        input: object | None = ...,  # noqa: A002 — Langfuse keyword
        output: object | None = ...,
        metadata: Mapping[str, str] | None = ...,
        level: str | None = ...,
        status_message: str | None = ...,
    ) -> object: ...

    def create_event(  # noqa: PLR0913 — mirrors the Langfuse SDK signature
        self,
        *,
        name: str,
        input: object | None = ...,  # noqa: A002 — Langfuse keyword
        output: object | None = ...,
        metadata: Mapping[str, object] | None = ...,
    ) -> object: ...


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
    session_id: str | None
    metadata: dict[str, str]
    tags: tuple[str, ...]


@dataclass
class PhaseTrace:
    """Handle for a phase: set the result before the phase exits."""

    name: str
    span: TraceSpan | None
    trace_input: object | None
    metadata: dict[str, str]
    tags: tuple[str, ...]
    user_id: str | None
    session_id: str | None
    output: object | None = None

    def set_output(self, output: object) -> None:
        """Record the phase result; Langfuse shows it as the trace output."""
        self.output = sanitize_trace_value(output)


_RUN_BASE: ContextVar[str | None] = ContextVar(
    "langfuse_generation_run_base", default=None
)
_RUN_DETAIL: ContextVar[str | None] = ContextVar(
    "langfuse_generation_run_detail", default=None
)
_ACTIVE: ContextVar[PhaseTrace | None] = ContextVar(
    "langfuse_active_phase_trace", default=None
)
_SCOPE: ContextVar[WorkflowTraceScope | None] = ContextVar(
    "langfuse_workflow_trace_scope",
    default=None,
)


def current_trace_scope() -> WorkflowTraceScope:
    """The scope set by the nearest enclosing ``workflow_trace_scope``."""
    return _SCOPE.get() or WorkflowTraceScope()


def current_phase_trace() -> PhaseTrace | None:
    """The phase trace an observation created now would attach to."""
    return _ACTIVE.get()


def current_generation_run_name(detail: str | None = None) -> str:
    """The generation name: phase base plus an optional unit-of-work detail."""
    base = _RUN_BASE.get() or TRACE_DEFAULT_RUN_NAME
    chosen = detail or _RUN_DETAIL.get()
    if not chosen:
        return base
    return f"{base}{TRACE_RUN_NAME_SEPARATOR}{chosen}"


@contextmanager
def workflow_trace_scope(scope: WorkflowTraceScope) -> Iterator[None]:
    """Overlay the non-empty fields of ``scope`` for the enclosed calls."""
    token = _SCOPE.set(_overlay(current_trace_scope(), scope))
    try:
        yield
    finally:
        _SCOPE.reset(token)


@contextmanager
def generation_run_name(detail: str) -> Iterator[None]:
    """Name enclosed generations after the phase plus ``detail``."""
    token = _RUN_DETAIL.set(detail)
    try:
        yield
    finally:
        _RUN_DETAIL.reset(token)


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
    project_id = resolved[TRACE_FIELD_PROJECT_ID]
    return PhaseTraceAttributes(
        name=TRACE_NAME_TEMPLATE.format(phase=phase),
        user_id=scope.user_id or None,
        session_id=project_id if project_id != TRACE_VALUE_UNKNOWN else None,
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
def phase_trace(
    metadata: Mapping[str, str],
    *,
    input: object | None = None,  # noqa: A002 — Langfuse keyword
) -> Iterator[PhaseTrace]:
    """Run the enclosed LLM calls inside the named, tagged phase trace.

    ``input`` is the phase brief (topic, attempt, model queue, ...). The result
    defaults to ``{"status": "completed"}'``; call ``trace.set_output(...)``
    before exiting to record a richer summary. An exception records a redacted
    error output and is re-raised.
    """
    attributes = build_phase_trace(metadata)
    trace_input = build_trace_input(attributes, input)
    active = _ACTIVE.get()
    if active is not None:
        _merge_active(active, attributes)
        yield active
        return

    run_base = (
        f"{attributes.metadata[TRACE_FIELD_CONTENT_TYPE]}"
        f".{attributes.metadata[TRACE_FIELD_PHASE]}"
    )
    client = get_langfuse_client()
    if client is None:
        run_token = _RUN_BASE.set(run_base)
        try:
            yield PhaseTrace(
                name=attributes.name,
                span=None,
                trace_input=trace_input,
                metadata=attributes.metadata,
                tags=attributes.tags,
                user_id=attributes.user_id,
                session_id=attributes.session_id,
            )
        finally:
            _RUN_BASE.reset(run_token)
        return

    with client.start_as_current_span(
        name=attributes.name,
        input=trace_input,
        metadata=attributes.metadata,
    ) as raw_span:
        span = cast(TraceSpan, raw_span)
        span.update_trace(
            name=attributes.name,
            user_id=attributes.user_id,
            session_id=attributes.session_id,
            input=trace_input,
            metadata=attributes.metadata,
            tags=list(attributes.tags),
        )
        handle = PhaseTrace(
            name=attributes.name,
            span=span,
            trace_input=trace_input,
            metadata=attributes.metadata,
            tags=attributes.tags,
            user_id=attributes.user_id,
            session_id=attributes.session_id,
        )
        active_token = _ACTIVE.set(handle)
        run_token = _RUN_BASE.set(run_base)
        try:
            with _propagate(attributes):
                try:
                    yield handle
                except Exception as exc:
                    _finish_error(handle, exc)
                    raise
                else:
                    _finish_success(handle)
        finally:
            _RUN_BASE.reset(run_token)
            _ACTIVE.reset(active_token)
            client.flush()


def sanitize_trace_value(value: object) -> object:
    """Redact secrets and bound the size of anything captured as trace I/O."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return redact_secrets(value)[:TRACE_IO_VALUE_MAX_CHARS]
    if isinstance(value, Mapping):
        return {
            redact_secrets(str(key))[
                :TRACE_METADATA_VALUE_MAX_CHARS
            ]: sanitize_trace_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [sanitize_trace_value(item) for item in value]
    return redact_secrets(str(value))[:TRACE_IO_VALUE_MAX_CHARS]


def build_trace_input(
    attributes: PhaseTraceAttributes,
    payload: object | None,
) -> dict[str, object]:
    """Put the actor metadata first, then the caller's phase brief."""
    base: dict[str, object] = {
        TRACE_FIELD_PROJECT_ID: attributes.metadata[TRACE_FIELD_PROJECT_ID],
        TRACE_FIELD_PHASE: attributes.metadata[TRACE_FIELD_PHASE],
        TRACE_FIELD_CONTENT_TYPE: attributes.metadata[TRACE_FIELD_CONTENT_TYPE],
        TRACE_FIELD_AGENT_NAME: attributes.metadata[TRACE_FIELD_AGENT_NAME],
    }
    sanitized = sanitize_trace_value(payload)
    if sanitized is None:
        return base
    if isinstance(sanitized, dict):
        return {**base, **sanitized}
    return {**base, "payload": sanitized}


def _finish_success(handle: PhaseTrace) -> None:
    output = handle.output
    if output is None:
        output = {TRACE_STATUS_FIELD: TRACE_OUTPUT_STATUS_COMPLETED}
    if handle.span is None:
        return
    handle.span.update(output=output)
    handle.span.update_trace(output=output)


def _finish_error(handle: PhaseTrace, error: Exception) -> None:
    message = redact_secrets(str(error))[:TRACE_IO_VALUE_MAX_CHARS]
    output = {
        TRACE_STATUS_FIELD: TRACE_OUTPUT_STATUS_ERROR,
        TRACE_ERROR_FIELD_TYPE: type(error).__name__,
        TRACE_ERROR_FIELD_MESSAGE: message,
    }
    if handle.span is None:
        return
    handle.span.update(
        output=output,
        level="ERROR",
        status_message=message,
    )
    handle.span.update_trace(output=output)


def _merge_active(active: PhaseTrace, attributes: PhaseTraceAttributes) -> None:
    """Keep the outer span and merge the nested phase metadata into it."""
    merged = {**active.metadata, **attributes.metadata}
    active.metadata = merged
    if active.span is None:
        return
    active.span.update(metadata=merged)
    active.span.update_trace(metadata=merged, tags=list(active.tags))


def _propagate(attributes: PhaseTraceAttributes) -> AbstractContextManager[object]:
    return _langfuse_propagate(
        trace_name=attributes.name,
        user_id=attributes.user_id,
        session_id=attributes.session_id,
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
    "PhaseTrace",
    "PhaseTraceAttributes",
    "TraceSpan",
    "WorkflowTraceScope",
    "build_phase_trace",
    "build_trace_input",
    "current_generation_run_name",
    "current_phase_trace",
    "current_trace_scope",
    "generation_run_name",
    "phase_trace",
    "sanitize_trace_value",
    "workflow_trace_scope",
]
