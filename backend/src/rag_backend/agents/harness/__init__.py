"""Shared Deep Agents harness (AE-0248).

One composition surface for the carousel orchestrator and the chat Deep Agents.
Grown incrementally; today it exposes the checkpointer provider, interrupt
helpers, middleware/store/memory providers, a typed ``DeepAgentConfig``, and the
``build_deep_agent`` builder. Chat agents get NO checkpointer (ADR-0013 / AE-0247).
"""

from rag_backend.agents.harness.builder import build_deep_agent
from rag_backend.agents.harness.checkpointer import (
    CheckpointerProvider,
    build_checkpointer,
)
from rag_backend.agents.harness.config import (
    AGENT_KIND_CHAT,
    AGENT_KIND_WORKFLOW,
    DeepAgentConfig,
)
from rag_backend.agents.harness.interrupts import iter_interrupt_values
from rag_backend.agents.harness.memory import resolve_memory_paths
from rag_backend.agents.harness.middleware import (
    build_human_in_the_loop_middleware,
    build_summarization_middleware,
)
from rag_backend.agents.harness.store import build_in_memory_store

__all__ = [
    "AGENT_KIND_CHAT",
    "AGENT_KIND_WORKFLOW",
    "CheckpointerProvider",
    "DeepAgentConfig",
    "build_checkpointer",
    "build_deep_agent",
    "build_human_in_the_loop_middleware",
    "build_in_memory_store",
    "build_summarization_middleware",
    "iter_interrupt_values",
    "resolve_memory_paths",
]
