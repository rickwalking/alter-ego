"""The notice ledger merge: a writer's change applied to what is committed now.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

import pytest

from rag_backend.modules.autopilot.domain.notice_log import (
    AttemptRecord,
    NoticeLog,
    ReviewRecord,
    StoredPending,
)
from rag_backend.modules.autopilot.domain.notice_merge import (
    LedgerChange,
    merge_change,
)

_P1 = StoredPending(owner_chat_id="42", phase="text")
_P2 = StoredPending(owner_chat_id="42", phase="design")


@pytest.mark.unit
class TestNoticeMerge:
    # Scenario: Concurrent notice ledger writes never erase a recorded review
    def test_a_stale_clear_never_drops_a_pending_reply_set_meanwhile(self) -> None:
        change = LedgerChange(base=NoticeLog(pending=_P1), new=NoticeLog())

        assert merge_change(NoticeLog(pending=_P2), change).pending == _P2
        assert merge_change(NoticeLog(pending=_P1), change).pending is None

    # Scenario: Concurrent notice ledger writes never erase a recorded review
    def test_concurrent_failures_all_count(self) -> None:
        base = NoticeLog(attempts=(AttemptRecord(key="review:4", count=1),))
        new = NoticeLog(attempts=(AttemptRecord(key="review:4", count=2),))
        current = NoticeLog(attempts=(AttemptRecord(key="review:4", count=2),))

        merged = merge_change(current, LedgerChange(base=base, new=new))

        assert merged.attempts == (AttemptRecord(key="review:4", count=3),)

    # Scenario: Concurrent notice ledger writes never erase a recorded review
    def test_a_removed_review_goes_and_others_stay(self) -> None:
        old = ReviewRecord(revision=4, album_ids=(1,), keyboard_id=9)
        other = ReviewRecord(revision=6, album_ids=(2,), keyboard_id=20)
        change = LedgerChange(base=NoticeLog(reviews=(old,)), new=NoticeLog())

        merged = merge_change(NoticeLog(reviews=(old, other)), change)

        assert merged.reviews == (other,)
