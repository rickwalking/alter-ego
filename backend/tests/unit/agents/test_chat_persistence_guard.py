"""Tests for the chat-persistence guard (ADR-0013).

Covers the `.feature` failure scenario (wiring a chat checkpointer is rejected)
as a seeded-violation test: the guard MUST trip on any non-None checkpointer, and
the chat-agent build modules must route through it.

See: tests/features/chat_persistence.feature
"""

from __future__ import annotations

import pytest

from rag_backend.agents import chat_persistence_guard
from rag_backend.agents.chat_persistence_guard import (
    ChatCheckpointerError,
    assert_no_chat_checkpointer,
)
from rag_backend.agents.harness import builder as harness_builder


def test_guard_allows_no_checkpointer() -> None:
    """None is the only allowed value."""
    assert assert_no_chat_checkpointer(None) is None


def test_guard_rejects_a_wired_checkpointer() -> None:
    """Any non-None checkpointer trips the guard, and the error explains why (the
    message-repository dual-write hazard), not just that it failed.
    """
    sentinel_checkpointer = object()
    with pytest.raises(ChatCheckpointerError) as exc:
        assert_no_chat_checkpointer(sentinel_checkpointer)
    assert "message_repository" in str(exc.value)
    assert "AE-0163" in str(exc.value)


def test_error_is_runtimeerror() -> None:
    assert issubclass(ChatCheckpointerError, RuntimeError)


def test_chat_agents_route_through_the_guard() -> None:
    """The chat agents build via the shared harness builder, which routes every chat
    config through the single guard, so the invariant is enforced at construction in one
    place.
    """
    assert (
        harness_builder.assert_no_chat_checkpointer
        is chat_persistence_guard.assert_no_chat_checkpointer
    )
