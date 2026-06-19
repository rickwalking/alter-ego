"""Shared Deep Agents harness — the builder (AE-0248).

:func:`build_deep_agent` is the single composition surface that wraps
``deepagents.create_deep_agent``. Both chat Deep Agents and (future) workflow
agents build through it from a typed :class:`DeepAgentConfig`, so persistence
defaults are enforced in one place:

- **Chat agents** (``AGENT_KIND_CHAT``) get **no** checkpointer. The build routes
  through ``assert_no_chat_checkpointer`` (ADR-0013 / AE-0247): a checkpointer is
  a second durable write path = the AE-0163 dual-write data-loss class. Requesting
  one fails the build loudly.
- **Workflow agents** (``AGENT_KIND_WORKFLOW``, e.g. carousel) may carry their
  existing single-writer checkpointer unchanged.

The harness stays generic — it never imports ``rag_backend.application``.
"""

from __future__ import annotations

from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph

from rag_backend.agents.chat_persistence_guard import assert_no_chat_checkpointer
from rag_backend.agents.harness.config import AGENT_KIND_CHAT, DeepAgentConfig
from rag_backend.agents.harness.memory import resolve_memory_paths


def build_deep_agent(config: DeepAgentConfig) -> CompiledStateGraph:
    """Compose a Deep Agent from a typed config, enforcing persistence defaults.

    Chat agents are guarded to carry no checkpointer (ADR-0013 / AE-0247);
    workflow agents may keep their single-writer checkpointer.
    """
    if config.agent_kind == AGENT_KIND_CHAT:
        assert_no_chat_checkpointer(config.checkpointer)

    return create_deep_agent(
        model=config.model,
        tools=list(config.tools),
        system_prompt=config.system_prompt,
        subagents=list(config.subagents),
        middleware=list(config.middleware),
        memory=resolve_memory_paths(config.memory) or None,
        checkpointer=config.checkpointer,
        store=config.store,
        name=config.name,
    )


__all__ = ["build_deep_agent"]
