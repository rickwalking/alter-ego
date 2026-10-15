"""A fake Langfuse client that records phase traces (AE-0390).

``install_trace_collector`` swaps the client ``phase_trace`` uses and the SDK's
``propagate_attributes`` for recorders. A fake LLM call reads
``collector.current()`` to learn which trace it ran in, the way a real
LangChain callback generation attaches to the active OTel span.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

import pytest

from rag_backend.infrastructure import langfuse_phase_trace


@dataclass
class RecordedTrace:
    """One opened phase trace: span + trace-level attributes."""

    name: str
    span_metadata: dict[str, str]
    trace_name: str = ""
    user_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    propagated: dict[str, object] = field(default_factory=dict)


@dataclass
class _FakeSpan:
    trace: RecordedTrace

    def update_trace(
        self,
        *,
        name: str,
        user_id: str | None,
        metadata: dict[str, str],
        tags: list[str],
    ) -> None:
        self.trace.trace_name = name
        self.trace.user_id = user_id
        self.trace.metadata = dict(metadata)
        self.trace.tags = list(tags)


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
        self, *, name: str, metadata: dict[str, str]
    ) -> Iterator[_FakeSpan]:
        trace = RecordedTrace(name=name, span_metadata=dict(metadata))
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


__all__ = ["RecordedTrace", "TraceCollector", "install_trace_collector"]
