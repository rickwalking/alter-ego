"""Shared Deep Agents harness — typed build config (AE-0248).

``DeepAgentConfig`` groups the inputs to :func:`build_deep_agent` so the builder
stays within the project's 3-argument limit and every field is statically typed
(no ``dict`` bundles). It is a plain dataclass — no Pydantic, since these are
already-validated internal composition inputs, not an API/service boundary.

The harness stays **generic**: it must not import ``rag_backend.application`` (the
``agents -> application`` edge is a down-only ratchet), so this config carries only
LangChain/Deep-Agents primitives, never carousel/chat domain objects.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

# Sentinel agent-kind tags — drive the no-chat-checkpointer guard in the builder.
AGENT_KIND_CHAT = "chat"
AGENT_KIND_WORKFLOW = "workflow"


@dataclass(frozen=True)
class DeepAgentConfig:
    """Typed inputs for :func:`build_deep_agent`.

    Attributes:
        model: the chat model backing the agent.
        name: the Deep Agent name (also used in traces).
        system_prompt: the system prompt string.
        agent_kind: ``AGENT_KIND_CHAT`` (no checkpointer allowed) or
            ``AGENT_KIND_WORKFLOW`` (carousel — single-writer checkpoint allowed).
        tools: the agent's tools.
        subagents: Deep Agents subagent specs.
        middleware: harness middleware presets (e.g. summarization).
        memory: per-agent ``AGENTS.md`` memory file paths passed to
            ``create_deep_agent(memory=...)``.
        checkpointer: workflow checkpointer; MUST be ``None`` for chat agents
            (enforced by the AE-0247 guard inside the builder).
        store: optional ``BaseStore`` for cross-thread memory.
    """

    model: BaseChatModel
    name: str
    system_prompt: str
    agent_kind: str = AGENT_KIND_CHAT
    tools: Sequence[BaseTool] = field(default_factory=tuple)
    subagents: Sequence[dict[str, object]] = field(default_factory=tuple)
    middleware: Sequence[AgentMiddleware] = field(default_factory=tuple)
    memory: Sequence[str] = field(default_factory=tuple)
    checkpointer: BaseCheckpointSaver | None = None
    store: BaseStore | None = None


__all__ = ["AGENT_KIND_CHAT", "AGENT_KIND_WORKFLOW", "DeepAgentConfig"]
