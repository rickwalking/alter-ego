"""Chat turns being written: one per conversation, drained at shutdown.

A turn runs as a detached task so a client disconnect cannot stop it; this
module keeps those tasks referenced, tells whether a conversation already has
one, streams a turn's events as they happen, and lets shutdown finish them.
"""

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

DETACHED_TURNS: set[asyncio.Task[None]] = set()
"""Turns still being written; kept referenced so a disconnect cannot drop them."""

BUSY_CONVERSATIONS: set[UUID] = set()
"""Conversations with a turn being written; a second turn waits for it to end."""


def conversation_turn_in_flight(conversation_id: UUID) -> bool:
    """Whether a reply for ``conversation_id`` is still being written."""
    return conversation_id in BUSY_CONVERSATIONS


async def drain_detached_turns(timeout_seconds: float) -> None:
    """Let the turns being written finish, then cancel any still running.

    Called at shutdown before the database closes. A cancelled turn saves the
    apology turn, so no question is left unanswered.
    """
    pending = list(DETACHED_TURNS)
    if not pending:
        return
    _, still_running = await asyncio.wait(pending, timeout=timeout_seconds)
    for turn in still_running:
        turn.cancel()
    await asyncio.gather(*still_running, return_exceptions=True)


async def stream_while_running(
    queue: asyncio.Queue[str], turn: asyncio.Task[None]
) -> AsyncIterator[str]:
    """Yield each event as the turn produces it, then whatever is left."""
    while not turn.done() or not queue.empty():
        if not queue.empty():
            yield queue.get_nowait()
            continue
        getter = asyncio.ensure_future(queue.get())
        try:
            await asyncio.wait({getter, turn}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            if not getter.done():
                getter.cancel()
        if getter.done() and not getter.cancelled():
            yield getter.result()


__all__ = [
    "BUSY_CONVERSATIONS",
    "DETACHED_TURNS",
    "conversation_turn_in_flight",
    "drain_detached_turns",
    "stream_while_running",
]
