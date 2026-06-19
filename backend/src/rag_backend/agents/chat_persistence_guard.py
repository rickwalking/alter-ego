"""Chat-persistence guard — ADR-0013 Option A (AE-0247).

The two chat Deep Agents (`rag_agent`, `alter_ego_agent`) are already stateful:
they persist every message to `message_repository` and rebuild history from
Postgres each turn. Giving them a LangGraph `checkpointer` would create a SECOND
durable write path keyed by `thread_id` — the exact AE-0163 dual-write data-loss
class. ADR-0013 resolves this: `message_repository` is canonical and the chat
agents get **no** checkpointer.

This module makes that decision executable and self-guarding: the chat-agent
build path calls :func:`assert_no_chat_checkpointer` so a checkpointer can never
be silently wired onto a chat thread. The shared harness builder (AE-0248) will
route its chat-agent construction through the same guard, keeping the single-
writer invariant enforceable as the composition surface grows.
"""

from __future__ import annotations

_ERR_CHAT_CHECKPOINTER = (
    "Chat Deep Agents must not be given a LangGraph checkpointer (ADR-0013, "
    "AE-0247). message_repository is the single canonical chat-persistence "
    "writer; a checkpointer is a second durable write path = the AE-0163 "
    "dual-write data-loss class. Persist chat turns via message_repository only."
)


class ChatCheckpointerError(RuntimeError):
    """Raised when a chat Deep Agent build is given a checkpointer (forbidden)."""


def assert_no_chat_checkpointer(checkpointer: object | None) -> None:
    """Enforce ADR-0013 Option A: a chat Deep Agent must have no checkpointer.

    Args:
        checkpointer: the checkpointer that would be wired to the chat agent —
            MUST be ``None``. Any non-``None`` value raises
            :class:`ChatCheckpointerError`.
    """
    if checkpointer is not None:
        raise ChatCheckpointerError(_ERR_CHAT_CHECKPOINTER)


__all__ = ["ChatCheckpointerError", "assert_no_chat_checkpointer"]
