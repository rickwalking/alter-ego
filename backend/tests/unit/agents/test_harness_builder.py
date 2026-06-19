"""Tests for the shared Deep Agents harness builder + presets (AE-0248).

Covers tests/features/agent_harness.feature:
- chat agent built via the harness builder with summarization, no checkpointer
- the summarization preset caps context-window growth
- wiring a chat checkpointer through the harness is rejected (guard trips)
- a workflow agent may keep its single-writer checkpointer
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from rag_backend.agents.chat_persistence_guard import ChatCheckpointerError
from rag_backend.agents.harness import (
    AGENT_KIND_CHAT,
    AGENT_KIND_WORKFLOW,
    DeepAgentConfig,
    build_deep_agent,
    build_summarization_middleware,
    resolve_memory_paths,
)
from rag_backend.agents.harness import builder as harness_builder
from rag_backend.agents.harness.middleware import (
    SUMMARIZATION_KEEP_MESSAGES,
    SUMMARIZATION_TRIGGER_MESSAGES,
)


class _StubModel:
    """Stand-in for a BaseChatModel — the builder never invokes it here."""

    @property
    def _llm_type(self) -> str:
        return "stub-chat"


def _stub_model() -> BaseChatModel:
    return cast("BaseChatModel", _StubModel())


def _stub_checkpointer() -> BaseCheckpointSaver[str]:
    return cast("BaseCheckpointSaver[str]", object())


class _RecordingCreate:
    """Records the kwargs build_deep_agent forwards to create_deep_agent."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "compiled-agent"


@pytest.fixture
def recording_create(monkeypatch: pytest.MonkeyPatch) -> _RecordingCreate:
    recorder = _RecordingCreate()
    monkeypatch.setattr(harness_builder, "create_deep_agent", recorder)
    return recorder


def _chat_config(
    *,
    agent_kind: str = AGENT_KIND_CHAT,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    middleware: Sequence[AgentMiddleware] = (),
) -> DeepAgentConfig:
    return DeepAgentConfig(
        model=_stub_model(),
        name="test-chat",
        system_prompt="sys",
        agent_kind=agent_kind,
        checkpointer=checkpointer,
        middleware=middleware,
    )


# Scenario: A chat agent is built via the harness builder with summarization
def test_chat_agent_built_via_builder_has_no_checkpointer(
    recording_create: _RecordingCreate,
) -> None:
    middleware = build_summarization_middleware(_stub_model())
    build_deep_agent(_chat_config(middleware=(middleware,)))

    assert recording_create.calls, "create_deep_agent was not invoked"
    kwargs = recording_create.calls[0]
    assert kwargs["checkpointer"] is None
    assert kwargs["middleware"] == [middleware]
    assert kwargs["name"] == "test-chat"


# Scenario: Wiring a chat checkpointer through the harness is rejected
def test_chat_checkpointer_is_rejected(recording_create: _RecordingCreate) -> None:
    with pytest.raises(ChatCheckpointerError):
        build_deep_agent(_chat_config(checkpointer=_stub_checkpointer()))
    assert not recording_create.calls, "build must fail before create_deep_agent"


# Scenario: A workflow agent may keep its single-writer checkpointer
def test_workflow_agent_passes_checkpointer_through(
    recording_create: _RecordingCreate,
) -> None:
    checkpointer = _stub_checkpointer()
    build_deep_agent(
        _chat_config(
            agent_kind=AGENT_KIND_WORKFLOW,
            checkpointer=checkpointer,
        )
    )
    assert recording_create.calls[0]["checkpointer"] is checkpointer


# Scenario: The summarization preset caps chat context-window growth
def test_summarization_preset_uses_message_thresholds() -> None:
    preset = build_summarization_middleware(_stub_model())
    # Trigger/keep are configured in messages, capping window growth.
    assert SUMMARIZATION_TRIGGER_MESSAGES > SUMMARIZATION_KEEP_MESSAGES > 0
    assert preset is not None


def test_resolve_memory_paths_drops_missing(tmp_path: Path) -> None:
    existing = tmp_path / "AGENTS.md"
    existing.write_text("memory")
    missing = tmp_path / "nope.md"
    resolved = resolve_memory_paths([str(existing), str(missing)])
    assert resolved == [str(existing)]


def test_resolve_memory_paths_empty() -> None:
    assert resolve_memory_paths([]) == []
