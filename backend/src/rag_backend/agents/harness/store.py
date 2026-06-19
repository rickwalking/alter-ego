"""Shared Deep Agents harness — store provider (AE-0248).

A minimal ``BaseStore`` provider for cross-thread agent memory. Today only the
in-memory store is wired (dev/ephemeral); a durable backend can be added behind
the same provider surface when a consumer needs it (AE-0250). Kept generic — no
carousel/chat coupling.
"""

from __future__ import annotations

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore


def build_in_memory_store() -> BaseStore:
    """Build an ephemeral in-memory ``BaseStore`` for cross-thread memory."""
    return InMemoryStore()


__all__ = ["build_in_memory_store"]
