"""Notice ledger round-trip (AE-0355)."""

from __future__ import annotations

from rag_backend.modules.autopilot.domain.notice_log import (
    AttemptRecord,
    NoticeLog,
    ReviewRecord,
    attempt_count,
    bump_attempt,
    dump_log,
    is_review_complete,
    notice_log_is_empty,
    parse_stored,
    record_reminder,
    record_review,
    record_status,
    reminder_revision,
)


def test_legacy_list_is_message_ids_without_a_review() -> None:
    log = parse_stored([4, 5])
    assert log.message_ids == (4, 5)
    assert is_review_complete(log, 1) is False
    assert notice_log_is_empty(NoticeLog()) is True


def test_dump_and_parse_keep_revision_and_attempts() -> None:
    log = record_review(
        NoticeLog(),
        ReviewRecord(revision=4, album_ids=(1, 2), keyboard_id=3),
    )
    log = record_status(log, "evt-9", 8)
    log = bump_attempt(log, "review:5")
    restored = parse_stored(dump_log(log))
    assert is_review_complete(restored, 4) is True
    assert is_review_complete(restored, 5) is False
    assert "evt-9" in restored.statuses
    assert 8 in restored.message_ids
    assert attempt_count(restored, "review:5") == 1
    assert reminder_revision(restored) == 4


def test_partial_album_is_not_a_complete_review() -> None:
    log = record_review(
        NoticeLog(),
        ReviewRecord(revision=1, album_ids=(1,), keyboard_id=None),
    )
    assert is_review_complete(log, 1) is False


def test_garbage_is_an_empty_log() -> None:
    assert parse_stored("nope").message_ids == ()
    stored = parse_stored({
        "reviews": {"nope": {"album": [1]}, "2": "bad"},
        "attempts": ["nope"],
        "statuses": [1, ""],
    })
    assert stored.reviews == ()
    assert stored.attempts == ()
    assert notice_log_is_empty(record_status(NoticeLog(), "evt", 1)) is False


def test_repeat_status_and_reminder_keep_one_entry() -> None:
    log = record_status(NoticeLog(), "evt-9", 8)
    again = record_status(log, "evt-9", 8)
    nudged = record_reminder(again, 4, 9)
    repeated = record_reminder(nudged, 4, 9)
    assert again.statuses == ("evt-9",)
    assert repeated.reminders == (4,)
    assert attempt_count(NoticeLog(attempts=()), "missing") == 0
    paired = NoticeLog(
        attempts=(
            AttemptRecord(key="other", count=1),
            AttemptRecord(key="review:1", count=2),
        )
    )
    assert attempt_count(paired, "review:1") == 2
