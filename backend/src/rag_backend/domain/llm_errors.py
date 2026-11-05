"""LLM call errors every layer may name.

``AllModelsUnavailableError`` is raised by the model queue (infrastructure) when no
queued model answers; the application layer catches it as a failed call, so it
lives here rather than next to the queue.
"""

from __future__ import annotations


class AllModelsUnavailableError(RuntimeError):
    """No model in the queue could answer (each one's state is named)."""


__all__ = ["AllModelsUnavailableError"]
