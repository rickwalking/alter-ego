"""Idempotency ledger stored in ``telegram_message_ids``.

A bare JSON list (runs that have never been notified) stays valid. Once a
notice is recorded the column becomes an object keyed by revision, event
id, and attempt count. Message ids are always kept in ``ids``.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.notify_constants import (
    LEDGER_ALBUM,
    LEDGER_ATTEMPTS,
    LEDGER_IDS,
    LEDGER_KEYBOARD,
    LEDGER_REMINDERS,
    LEDGER_REVIEWS,
    LEDGER_STATUSES,
)


@dataclass(frozen=True, kw_only=True)
class ReviewRecord:
    """One owner review for a single revision number."""

    revision: int
    album_ids: tuple[int, ...]
    keyboard_id: int | None


@dataclass(frozen=True, kw_only=True)
class AttemptRecord:
    """How many non-429 failures a notice key has had."""

    key: str
    count: int


@dataclass(frozen=True, kw_only=True)
class NoticeLog:
    """What has already been delivered for one run."""

    reviews: tuple[ReviewRecord, ...] = ()
    reminders: tuple[int, ...] = ()
    statuses: tuple[str, ...] = ()
    attempts: tuple[AttemptRecord, ...] = ()
    message_ids: tuple[int, ...] = ()


def notice_log_is_empty(log: NoticeLog) -> bool:
    """True when nothing has been recorded yet."""
    if log.reviews or log.reminders or log.statuses or log.attempts:
        return False
    return not log.message_ids


def find_review(log: NoticeLog, revision: int) -> ReviewRecord | None:
    """The stored review for ``revision``, if one was started or finished."""
    for review in log.reviews:
        if review.revision == revision:
            return review
    return None


def is_review_complete(log: NoticeLog, revision: int) -> bool:
    """True once the keyboard message for this revision was stored."""
    review = find_review(log, revision)
    return review is not None and review.keyboard_id is not None


def attempt_count(log: NoticeLog, key: str) -> int:
    """Failures already recorded for ``key``."""
    for item in log.attempts:
        if item.key == key:
            return item.count
    return 0


def reminder_revision(log: NoticeLog) -> int:
    """The revision a nudge refers to. Zero when no review was stored."""
    if not log.reviews:
        return 0
    return max(review.revision for review in log.reviews)


def record_review(log: NoticeLog, review: ReviewRecord) -> NoticeLog:
    """Replace any partial review for the same revision and append its ids."""
    kept = tuple(item for item in log.reviews if item.revision != review.revision)
    return NoticeLog(
        reviews=(*kept, review),
        reminders=log.reminders,
        statuses=log.statuses,
        attempts=log.attempts,
        message_ids=_merge_ids(log.message_ids, _review_ids(review)),
    )


def record_status(log: NoticeLog, event_id: str, message_id: int) -> NoticeLog:
    """Remember one status event so a replay does not send it again."""
    statuses = log.statuses
    if event_id not in statuses:
        statuses = (*statuses, event_id)
    return NoticeLog(
        reviews=log.reviews,
        reminders=log.reminders,
        statuses=statuses,
        attempts=log.attempts,
        message_ids=_merge_ids(log.message_ids, (message_id,)),
    )


def record_reminder(log: NoticeLog, revision: int, message_id: int) -> NoticeLog:
    """Remember one nudge for ``revision``."""
    reminders = log.reminders
    if revision not in reminders:
        reminders = (*reminders, revision)
    return NoticeLog(
        reviews=log.reviews,
        reminders=reminders,
        statuses=log.statuses,
        attempts=log.attempts,
        message_ids=_merge_ids(log.message_ids, (message_id,)),
    )


def bump_attempt(log: NoticeLog, key: str) -> NoticeLog:
    """Count one failed send. Does not add a message id."""
    count = attempt_count(log, key) + 1
    kept = tuple(item for item in log.attempts if item.key != key)
    return NoticeLog(
        reviews=log.reviews,
        reminders=log.reminders,
        statuses=log.statuses,
        attempts=(*kept, AttemptRecord(key=key, count=count)),
        message_ids=log.message_ids,
    )


def dump_log(log: NoticeLog) -> dict[str, object]:
    """JSON object written to ``telegram_message_ids``."""
    reviews: dict[str, dict[str, object]] = {}
    for review in log.reviews:
        reviews[str(review.revision)] = {
            LEDGER_ALBUM: list(review.album_ids),
            LEDGER_KEYBOARD: review.keyboard_id,
        }
    attempts = {item.key: item.count for item in log.attempts}
    return {
        LEDGER_IDS: list(log.message_ids),
        LEDGER_REVIEWS: reviews,
        LEDGER_REMINDERS: list(log.reminders),
        LEDGER_STATUSES: list(log.statuses),
        LEDGER_ATTEMPTS: attempts,
    }


def parse_stored(raw: object) -> NoticeLog:
    """Read a legacy id list or a notice object. Anything else is empty."""
    if isinstance(raw, list):
        return NoticeLog(message_ids=_ints(raw))
    if isinstance(raw, dict):
        return _from_object(raw)
    return NoticeLog()


def _from_object(raw: dict[str, object]) -> NoticeLog:
    return NoticeLog(
        reviews=_reviews(raw.get(LEDGER_REVIEWS)),
        reminders=_ints(raw.get(LEDGER_REMINDERS)),
        statuses=_strings(raw.get(LEDGER_STATUSES)),
        attempts=_attempts(raw.get(LEDGER_ATTEMPTS)),
        message_ids=_ints(raw.get(LEDGER_IDS)),
    )


def _reviews(raw: object) -> tuple[ReviewRecord, ...]:
    if not isinstance(raw, dict):
        return ()
    records: list[ReviewRecord] = []
    for key, value in raw.items():
        revision = _key_int(key)
        if revision is None or not isinstance(value, dict):
            continue
        records.append(_review(revision, value))
    return tuple(records)


def _review(revision: int, value: dict[str, object]) -> ReviewRecord:
    return ReviewRecord(
        revision=revision,
        album_ids=_ints(value.get(LEDGER_ALBUM)),
        keyboard_id=_optional_int(value.get(LEDGER_KEYBOARD)),
    )


def _attempts(raw: object) -> tuple[AttemptRecord, ...]:
    if not isinstance(raw, dict):
        return ()
    records: list[AttemptRecord] = []
    for key, value in raw.items():
        count = _optional_int(value)
        if isinstance(key, str) and count is not None:
            records.append(AttemptRecord(key=key, count=count))
    return tuple(records)


def _review_ids(review: ReviewRecord) -> tuple[int, ...]:
    if review.keyboard_id is None:
        return review.album_ids
    return (*review.album_ids, review.keyboard_id)


def _merge_ids(current: tuple[int, ...], extra: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys((*current, *extra)))


def _ints(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return ()
    values = [_optional_int(item) for item in raw]
    return tuple(item for item in values if item is not None)


def _strings(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, str) and item)


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _key_int(value: object) -> int | None:
    if not isinstance(value, str) or not value.isdigit():
        return None
    return int(value)
