"""A run the generation queue parked: its notice, buttons and owner retry. Pure.

The queue parks an autopilot run with reason ``queue_dead_letter:<code>``: from
``generating`` or ``reworking`` it is ``escalated``, before it started it is
``failed``. The notice explains the code and offers "Tentar de novo" and
"Descartar". An escalated run resumes from its checkpoint; a failed one is
terminal, so the retry queues a new run for the same theme.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    StatusCopy,
    status_text,
)
from rag_backend.modules.autopilot.notify_constants import KIND_ESCALATED, KIND_FAILED
from rag_backend.modules.autopilot.queue_constants import (
    BUTTON_DEAD_DISCARD,
    BUTTON_DEAD_RETRY,
    CALLBACK_DEAD_DISCARD_PREFIX,
    CALLBACK_DEAD_RETRY_PREFIX,
    DEAD_LETTER_TEXT_BY_CODE,
    DEAD_LETTER_TEXT_DEFAULT,
    REASON_DEAD_LETTER_PREFIX,
    TEXT_DEAD_LETTER,
)

_PARKED_KINDS = frozenset({KIND_ESCALATED, KIND_FAILED})


@dataclass(frozen=True, kw_only=True)
class RetryFailedCommand:
    """Queue ``new_run_id`` for the theme of the failed run ``run_id``, once."""

    run_id: UUID
    new_run_id: UUID
    created_at: datetime


class DeadLetterRuns(Protocol):
    """Owner retry of a run the queue failed before it started; caller commits."""

    async def retry_failed(self, command: RetryFailedCommand) -> bool:
        """Mark the failed run retried and queue the new run; False when already."""
        ...

    async def discard_failed(self, run_id: UUID) -> bool:
        """Mark the failed run discarded; False when it was already resolved."""
        ...


def is_dead_letter(reason: str | None) -> bool:
    """True for a reason the generation queue wrote when it parked the run."""
    return bool(reason) and str(reason).startswith(REASON_DEAD_LETTER_PREFIX)


def dead_letter_text(reason: str) -> str:
    """The owner notice for a parked run, with the reason in plain words."""
    code = reason.removeprefix(REASON_DEAD_LETTER_PREFIX)
    explanation = DEAD_LETTER_TEXT_BY_CODE.get(
        code, DEAD_LETTER_TEXT_DEFAULT.format(code=code)
    )
    return TEXT_DEAD_LETTER.format(reason=explanation)


def dead_letter_keyboard(run_id: UUID) -> InlineKeyboard:
    """ "Tentar de novo" and "Descartar" for one parked run."""
    return InlineKeyboard(
        rows=(
            (
                InlineButton(
                    text=BUTTON_DEAD_RETRY,
                    callback_data=f"{CALLBACK_DEAD_RETRY_PREFIX}{run_id}",
                ),
                InlineButton(
                    text=BUTTON_DEAD_DISCARD,
                    callback_data=f"{CALLBACK_DEAD_DISCARD_PREFIX}{run_id}",
                ),
            ),
        )
    )


def is_parked_notice(kind: str, reason: str) -> bool:
    """An escalated or failed notice whose reason is a queue dead letter."""
    return kind in _PARKED_KINDS and is_dead_letter(reason)


def status_body(kind: str, copy: StatusCopy) -> str:
    """The status text; a queue dead letter gets its own explanation."""
    if is_parked_notice(kind, copy.reason):
        return dead_letter_text(copy.reason)
    return status_text(kind, copy)


__all__ = [
    "DeadLetterRuns",
    "RetryFailedCommand",
    "dead_letter_keyboard",
    "dead_letter_text",
    "is_dead_letter",
    "is_parked_notice",
    "status_body",
]
