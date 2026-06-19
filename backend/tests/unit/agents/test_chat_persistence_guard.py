"""Tests for the chat-persistence guard (AE-0247 / ADR-0013).

Covers the `.feature` failure scenario (wiring a chat checkpointer is rejected)
as a seeded-violation test: the guard MUST trip on any non-None checkpointer, and
the chat-agent build modules must route through it.

See: tests/features/chat_persistence.feature
"""

from __future__ import annotations

import pytest

from rag_backend.agents import alter_ego_agent, chat_persistence_guard, rag_agent
from rag_backend.agents.chat_persistence_guard import (
    ChatCheckpointerError,
    assert_no_chat_checkpointer,
)


def test_guard_allows_no_checkpointer() -> None:
    # Option-A default: None is the only allowed value (does not raise).
    assert assert_no_chat_checkpointer(None) is None


def test_guard_rejects_a_wired_checkpointer() -> None:
    # Seeded violation: any non-None checkpointer trips the guard.
    sentinel_checkpointer = object()
    with pytest.raises(ChatCheckpointerError) as exc:
        assert_no_chat_checkpointer(sentinel_checkpointer)
    # The error explains WHY (the AE-0163 dual-write class), not just THAT.
    assert "message_repository" in str(exc.value)
    assert "AE-0163" in str(exc.value)


def test_error_is_runtimeerror() -> None:
    assert issubclass(ChatCheckpointerError, RuntimeError)


def test_chat_agents_route_through_the_guard() -> None:
    # Both chat-agent build modules import and use the single guard, so the
    # invariant is enforced at construction (not duplicated/forked).
    assert (
        rag_agent.assert_no_chat_checkpointer
        is chat_persistence_guard.assert_no_chat_checkpointer
    )
    assert (
        alter_ego_agent.assert_no_chat_checkpointer
        is chat_persistence_guard.assert_no_chat_checkpointer
    )
