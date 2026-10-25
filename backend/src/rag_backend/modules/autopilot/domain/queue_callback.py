"""Parse the queue buttons' callback data. No I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.autopilot.queue_constants import CALLBACK_QUEUE_PATTERN

_QUEUE = re.compile(CALLBACK_QUEUE_PATTERN)


@dataclass(frozen=True, kw_only=True)
class QueueCallback:
    """A dead-letter or "Gerar agora" tap: the action and the run or theme id."""

    kind: str
    target: UUID


def parse_queue_callback(data: str) -> QueueCallback | None:
    """``ap:qrt|qdc|qnow:<uuid>``; anything else is None."""
    match = _QUEUE.fullmatch(data)
    if match is None:
        return None
    return QueueCallback(kind=match.group(1), target=UUID(match.group(2)))


__all__ = ["QueueCallback", "parse_queue_callback"]
