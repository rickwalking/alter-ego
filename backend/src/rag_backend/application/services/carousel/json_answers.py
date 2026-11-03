"""The port for an LLM call whose JSON answer is parsed.

The retrying implementation (re-roll, repair, then the fallback model) lives in the
agents layer and is injected by the orchestrator, so the application layer adds no
import of the agents layer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

T = TypeVar("T")


class JsonAnswers(Protocol):
    """Ask ``prompt`` and return the answer parsed by ``parse``."""

    async def __call__(self, prompt: str, parse: Callable[[str], T]) -> T:
        """The parsed answer; ``parse``'s ``ValueError``/``TypeError`` when none parses."""
        ...


__all__ = ["JsonAnswers"]
