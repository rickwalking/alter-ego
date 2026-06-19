"""Shared Deep Agents harness (AE-0248).

One composition surface for the carousel orchestrator and the chat Deep Agents.
Grown incrementally; today it exposes the checkpointer provider relocated from the
composition root. Chat agents get NO checkpointer (ADR-0013 / AE-0247).
"""

from rag_backend.agents.harness.checkpointer import (
    CheckpointerProvider,
    build_checkpointer,
)

__all__ = ["CheckpointerProvider", "build_checkpointer"]
