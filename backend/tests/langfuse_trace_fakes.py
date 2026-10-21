"""A fake Langfuse client that records phase traces (AE-0390, AE-0442).

``install_trace_collector`` swaps the client ``phase_trace`` uses and the SDK's
``propagate_attributes`` for recorders. A fake LLM call reads
``collector.current()`` to learn which trace it ran in, the way a real
LangChain callback generation attaches to the active OTel span.

AE-0442: the fake also captures the trace/span input and output, the session id,
span updates and events, so tests can prove the Langfuse list is not empty.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

import pytest

from rag_backend.infrastructure import langfuse_phase_trace


@dataclass
class RecordedEvent:
    """One event created inside a trace."""

    name: str
    input: object | None = None
    output: object | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class RecordedTrace:
    """One opened phase trace: span + trace-level attributes."""

    name: str
    span_metadata: dict[str, object]
    span_input: object | None = None
    span_output: object | None = None
    trace_name: str = ""
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    input: object | None = None
    output: object | None = None
    level: str | None = None
    status_message: str | None = None
    propagated: dict[str, object] = field(default_factory=dict)
    events: list[RecordedEvent] = field(default_factory=list)


@dataclass
class _FakeSpan:
    trace: RecordedTrace

    @property
    def name(self) -> str:
        return self.trace.name

    def update_trace(
        self,
        *,
        name: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, object] | None = None,
        tags: list[str] | None = None,
        input: object | None = None,
        output: object | None = None,
    ) -> None:
        if name is not None:
            self.trace.trace_name = name
        if user_id is not None:
            self.trace.user_id = user_id
        if session_id is not None:
            self.trace.session_id = session_id
        if metadata is not None:
            self.trace.metadata = dict(metadata)
        if tags is not None:
            self.trace.tags = list(tags)
        if input is not None:
            self.trace.input = input
        if output is not None:
            self.trace.output = output

    def update(
        self,
        *,
        name: str | None = None,
        input: object | None = None,
        output: object | None = None,
        metadata: dict[str, object] | None = None,
        level: str | None = None,
        status_message: str | None = None,
    ) -> None:
        if name is not None:
            self.trace.name = name
        if input is not None:
            self.trace.span_input = input
        if output is not None:
            self.trace.span_output = output
        if metadata is not None:
            self.trace.span_metadata = dict(metadata)
        if level is not None:
            self.trace.level = level
        if status_message is not None:
            self.trace.status_message = status_message

    def create_event(
        self,
        *,
        name: str,
        input: object | None = None,
        output: object | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RecordedEvent:
        event = RecordedEvent(
            name=name,
            input=input,
            output=output,
            metadata=dict(metadata or {}),
        )
        self.trace.events.append(event)
        return event


class TraceCollector:
    """Fake Langfuse client: records traces and the one active per context."""

    def __init__(self) -> None:
        self.traces: list[RecordedTrace] = []
        self.flushes = 0
        self._active: ContextVar[RecordedTrace | None] = ContextVar(
            "fake_langfuse_active_trace", default=None
        )

    def current(self) -> RecordedTrace | None:
        """The trace an LLM call made now would attach to."""
        return self._active.get()

    @contextmanager
    def start_as_current_span(
        self,
        *,
        name: str,
        input: object | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Iterator[_FakeSpan]:
        trace = RecordedTrace(
            name=name,
            span_metadata=dict(metadata or {}),
            span_input=input,
        )
        self.traces.append(trace)
        token = self._active.set(trace)
        try:
            yield _FakeSpan(trace)
        finally:
            self._active.reset(token)

    def flush(self) -> None:
        self.flushes += 1

    @contextmanager
    def propagate(self, **attributes: object) -> Iterator[object]:
        trace = self.current()
        if trace is not None:
            trace.propagated = dict(attributes)
        yield None


def install_trace_collector(monkeypatch: pytest.MonkeyPatch) -> TraceCollector:
    """Route ``phase_trace`` to a fresh collector for this test."""
    collector = TraceCollector()
    monkeypatch.setattr(langfuse_phase_trace, "get_langfuse_client", lambda: collector)
    monkeypatch.setattr(
        langfuse_phase_trace, "_langfuse_propagate", collector.propagate
    )
    return collector


__all__ = [
    "RecordedEvent",
    "RecordedTrace",
    "TraceCollector",
    "install_trace_collector",
]
