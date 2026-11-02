"""Apply one writer's change to the notice ledger as committed now. No I/O.

Several writers (the notifier, the pending reply, the queue and thesis
prompts, the queue bridge) each read a run, compute a new ledger from that read
(``base``) and save it. Saving the whole ledger would erase what another writer
recorded meanwhile, such as a review keyboard an approve now depends on. The
store therefore re-reads the committed ledger under a row lock (``current``) and
applies only this writer's difference (``base -> new``) to it.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from rag_backend.modules.autopilot.domain.notice_log import (
    AttemptRecord,
    NoticeLog,
    ReviewRecord,
    StoredPending,
)

_T = TypeVar("_T", bound=Hashable)


@dataclass(frozen=True, kw_only=True)
class LedgerChange:
    """The ledger a writer read and the one it computed from it."""

    base: NoticeLog
    new: NoticeLog


def merge_change(current: NoticeLog, change: LedgerChange) -> NoticeLog:
    """``current`` with exactly the writer's additions, removals and updates."""
    base, new = change.base, change.new
    return NoticeLog(
        reviews=_by_key(current.reviews, (base.reviews, new.reviews), _revision),
        reminders=_items(current.reminders, (base.reminders, new.reminders)),
        statuses=_items(current.statuses, (base.statuses, new.statuses)),
        attempts=_attempts(current.attempts, (base.attempts, new.attempts)),
        message_ids=_items(current.message_ids, (base.message_ids, new.message_ids)),
        pending=_pending(current, change),
        reminder_messages=_items(
            current.reminder_messages, (base.reminder_messages, new.reminder_messages)
        ),
    )


def _pending(current: NoticeLog, change: LedgerChange) -> StoredPending | None:
    """The writer's pending change, unless another writer changed it meanwhile."""
    if change.new.pending == change.base.pending:
        return current.pending
    if current.pending != change.base.pending:
        return current.pending
    return change.new.pending


def _attempts(
    current: tuple[AttemptRecord, ...],
    diff: tuple[tuple[AttemptRecord, ...], tuple[AttemptRecord, ...]],
) -> tuple[AttemptRecord, ...]:
    """Failure counts merge as increments, so concurrent failures all count."""
    base = {item.key: item.count for item in diff[0]}
    counts = {item.key: item.count for item in current}
    for item in diff[1]:
        delta = item.count - base.get(item.key, 0)
        if delta:
            counts[item.key] = counts.get(item.key, 0) + delta
    return tuple(AttemptRecord(key=key, count=count) for key, count in counts.items())


def _revision(review: ReviewRecord) -> int:
    return review.revision


def _items(
    current: tuple[_T, ...], diff: tuple[Iterable[_T], Iterable[_T]]
) -> tuple[_T, ...]:
    """Ordered set difference applied: ``new - base`` added, ``base - new`` removed."""
    base, new = tuple(diff[0]), tuple(diff[1])
    removed = set(base) - set(new)
    kept = [item for item in current if item not in removed]
    added = [item for item in new if item not in set(base) and item not in kept]
    return (*kept, *added)


_R = TypeVar("_R", ReviewRecord, AttemptRecord)
"""A record keyed in the ledger (reviews by revision)."""


def _by_key(
    current: tuple[_R, ...],
    diff: tuple[tuple[_R, ...], tuple[_R, ...]],
    key: Callable[[_R], Hashable],
) -> tuple[_R, ...]:
    """Records keyed by ``key``: the writer's changed keys win, removed keys go."""
    base: dict[Hashable, _R] = {key(item): item for item in diff[0]}
    new: dict[Hashable, _R] = {key(item): item for item in diff[1]}
    changed: dict[Hashable, _R] = {k: v for k, v in new.items() if base.get(k) != v}
    removed = set(base) - set(new)
    kept: list[_R] = [
        changed.pop(key(item), item) for item in current if key(item) not in removed
    ]
    return tuple(kept + list(changed.values()))


__all__ = ["LedgerChange", "merge_change"]
