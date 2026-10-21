"""Owner notice dispatch, dedupe, and the 24 hour reminder.

Gherkin: tests/features/autopilot_telegram_notify.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.notifications import (
    NotificationDependencies,
    OwnerNotificationService,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_PUBLISH_NOTICE,
    EVENT_TYPE_READY_FOR_OWNER,
    EVENT_TYPE_STATE_CHANGED,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    ReviewRecord,
    bump_attempt,
    record_reminder,
    record_review,
)
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    ReviewFacts,
    ReviewNotice,
    ReviewSendResult,
    SaveNoticeLog,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.notify_constants import (
    EVENT_TYPE_IG_EXPIRING,
    KIND_IG_EXPIRING,
    NOTIFY_BATCH,
    NOTIFY_MAX_ATTEMPTS,
    REMINDER_AFTER_HOURS,
)

_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
_RUN = UUID("33333333-3333-4333-8333-333333333333")
_PROJECT = "carousel-1"


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Events:
    items: list[AutopilotOutboxEvent] = field(default_factory=list)
    advanced: list[str] = field(default_factory=list)

    async def recent(self) -> list[AutopilotOutboxEvent]:
        return list(self.items)

    async def advance(self, event: AutopilotOutboxEvent) -> None:
        self.advanced.append(event.event_id)


@dataclass
class _Runs:
    run: AutopilotRun | None
    extra: list[AutopilotRun] = field(default_factory=list)

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        if self.run is None or self.run.run_id != run_id:
            return None
        return self.run

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        matched: list[AutopilotRun] = []
        if self.run is not None and self.run.state is query.state:
            matched.append(self.run)
        matched.extend(item for item in self.extra if item.state is query.state)
        return matched


def _default_facts() -> ReviewFacts:
    return ReviewFacts(
        title="Agents",
        caption="The caption",
        slide_paths=("a.jpg", "b.jpg"),
    )


@dataclass
class _Facts:
    facts: ReviewFacts | None = field(default_factory=_default_facts)

    async def load(self, project_id: str) -> ReviewFacts | None:
        assert project_id == _PROJECT
        return self.facts


@dataclass
class _Store:
    saved: list[SaveNoticeLog] = field(default_factory=list)

    async def save(self, command: SaveNoticeLog) -> None:
        self.saved.append(command)
        if command.run_id == _RUN:
            return


@dataclass
class _Notifier:
    reviews: list[ReviewNotice] = field(default_factory=list)
    statuses: list[StatusNotice] = field(default_factory=list)
    error: Exception | None = None

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        if self.error is not None:
            raise self.error
        self.reviews.append(notice)
        return ReviewSendResult(album_ids=(1, 2), keyboard_id=3)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if self.error is not None:
            raise self.error
        self.statuses.append(notice)
        return StatusSendResult(message_id=9)


def _run(
    state: AutopilotRunState = AutopilotRunState.AWAITING_OWNER,
    log: NoticeLog | None = None,
    updated_at: datetime | None = None,
) -> AutopilotRun:
    return AutopilotRun(
        run_id=_RUN,
        topic_candidate_id=uuid4(),
        carousel_project_id=_PROJECT,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=() if log is None else log.message_ids,
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        updated_at=updated_at,
        notice_log=log or NoticeLog(),
    )


def _event(
    event_type: str,
    payload: dict[str, object],
    event_id: str = "evt-1",
) -> AutopilotOutboxEvent:
    return AutopilotOutboxEvent(
        event_id=event_id,
        event_type=event_type,
        run_id=_RUN,
        payload=payload,
        created_at=_NOW,
    )


def _service(
    events: _Events,
    runs: _Runs,
    notifier: _Notifier,
    facts: _Facts | None = None,
    configured: bool = True,
    chat_id: str = "42",
) -> tuple[OwnerNotificationService, _Store]:
    store = _Store()
    deps = NotificationDependencies(
        events=events,
        runs=runs,
        facts=facts or _Facts(),
        notices=store,
        notifier=notifier,
        clock=_Clock(),
        chat_id=chat_id,
        configured=configured,
        web_base_url="https://marinssolutions.com",
    )
    return OwnerNotificationService(deps), store


@pytest.mark.asyncio
async def test_ready_event_sends_one_review() -> None:
    """Scenario: Owner receives slides and buttons."""
    event = _event(
        EVENT_TYPE_READY_FOR_OWNER,
        {
            "project_id": _PROJECT,
            "revision": 4,
            "persona_score": 88,
            "sources_count": 3,
        },
    )
    notifier = _Notifier()
    service, store = _service(_Events([event]), _Runs(_run()), notifier)
    assert await service.tick() == 1
    assert len(notifier.reviews) == 1
    assert notifier.reviews[0].slide_paths == ("a.jpg", "b.jpg")
    assert notifier.reviews[0].persona_score == 88.0
    assert notifier.reviews[0].sources_count == 3
    assert store.saved[0].log.reviews[0].revision == 4
    assert store.saved[0].log.reviews[0].keyboard_id == 3


@pytest.mark.asyncio
async def test_duplicate_revision_does_not_call_telegram() -> None:
    """Scenario: Duplicate event is ignored."""
    event = _event(EVENT_TYPE_READY_FOR_OWNER, {"project_id": _PROJECT, "revision": 4})
    log = record_review(
        NoticeLog(),
        ReviewRecord(revision=4, album_ids=(1,), keyboard_id=2),
    )
    notifier = _Notifier()
    service, store = _service(_Events([event]), _Runs(_run(log=log)), notifier)
    assert await service.tick() == 0
    assert notifier.reviews == []
    assert store.saved == []


@pytest.mark.asyncio
async def test_rate_limit_is_not_counted_as_a_failure() -> None:
    """Scenario: Rate limited."""
    event = _event(EVENT_TYPE_READY_FOR_OWNER, {"project_id": _PROJECT, "revision": 1})
    notifier = _Notifier(error=TelegramRateLimitedError("telegram_rate_limited"))
    service, store = _service(_Events([event]), _Runs(_run()), notifier)
    assert await service.tick() == 0
    assert store.saved == []


@pytest.mark.asyncio
async def test_other_errors_retry_then_drop() -> None:
    event = _event(
        EVENT_TYPE_STATE_CHANGED, {"state": "failed", "reason": "phase_failed"}
    )
    log = NoticeLog()
    for _ in range(NOTIFY_MAX_ATTEMPTS - 1):
        log = bump_attempt(log, "status:evt-1")
    notifier = _Notifier(error=TelegramDeliveryError("telegram_http_500"))
    service, store = _service(
        _Events([event]),
        _Runs(_run(state=AutopilotRunState.FAILED, log=log)),
        notifier,
    )
    assert await service.tick() == 0
    assert store.saved[0].log.attempts[-1].count == NOTIFY_MAX_ATTEMPTS
    notifier.error = None
    runs = _Runs(_run(state=AutopilotRunState.FAILED, log=store.saved[0].log))
    service, store = _service(_Events([event]), runs, notifier)
    assert await service.tick() == 0
    assert notifier.statuses == []


@pytest.mark.asyncio
async def test_escalated_status_includes_reason_and_link() -> None:
    """Scenario: Escalated run includes the reason and a link."""
    event = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "escalated", "reason": "persona_score_below_threshold"},
    )
    notifier = _Notifier()
    service, _store = _service(
        _Events([event]),
        _Runs(_run(state=AutopilotRunState.ESCALATED)),
        notifier,
    )
    assert await service.tick() == 1
    text = notifier.statuses[0].text
    assert "persona_score_below_threshold" in text
    assert "https://marinssolutions.com/dashboard/create/carousel-1" in text


@pytest.mark.asyncio
async def test_published_and_failed_and_token_messages() -> None:
    """Scenario: Published run includes the permalink."""
    published = _event(
        EVENT_TYPE_PUBLISH_NOTICE,
        {"outcome": "published", "permalink": "https://instagram.com/p/abc"},
        event_id="pub",
    )
    failed = _event(
        EVENT_TYPE_PUBLISH_NOTICE,
        {"outcome": "publish_failed", "error_code": "36003", "offer_retry": True},
        event_id="fail",
    )
    token = _event(
        EVENT_TYPE_IG_EXPIRING,
        {"days_remaining": 6},
        event_id="tok",
    )
    notifier = _Notifier()
    service, _store = _service(
        _Events([published, failed, token]),
        _Runs(_run(state=AutopilotRunState.PUBLISHED)),
        notifier,
    )
    assert await service.tick() == 3
    texts = [notice.text for notice in notifier.statuses]
    assert any("https://instagram.com/p/abc" in text for text in texts)
    assert any("36003" in text for text in texts)
    assert any("6" in text for text in texts)
    keyboards = [notice.keyboard for notice in notifier.statuses]
    assert any(
        keyboard is not None and "retry" in keyboard.rows[0][0].callback_data
        for keyboard in keyboards
    )
    assert KIND_IG_EXPIRING


@pytest.mark.asyncio
async def test_reminder_is_sent_once() -> None:
    """Scenario: Awaiting owner is reminded once."""
    updated = _NOW - timedelta(hours=REMINDER_AFTER_HOURS, minutes=1)
    run = _run(updated_at=updated)
    notifier = _Notifier()
    events = _Events([])
    service, store = _service(events, _Runs(run), notifier)
    assert await service.tick() == 1
    assert len(notifier.statuses) == 1
    reminded = record_reminder(NoticeLog(), 0, notifier.statuses[0] and 9)
    reminded = store.saved[0].log
    second, _store = _service(
        events, _Runs(_run(updated_at=updated, log=reminded)), _Notifier()
    )
    assert await second.tick() == 0


@pytest.mark.asyncio
async def test_fresh_awaiting_owner_is_not_reminded() -> None:
    run = _run(updated_at=_NOW)
    notifier = _Notifier()
    service, _store = _service(_Events([]), _Runs(run), notifier)
    assert await service.tick() == 0
    assert notifier.statuses == []


@pytest.mark.asyncio
async def test_unconfigured_notifier_is_a_no_op() -> None:
    """Scenario: Missing bot token escalates and does not call Telegram."""
    event = _event(EVENT_TYPE_READY_FOR_OWNER, {"project_id": _PROJECT, "revision": 1})
    notifier = _Notifier()
    service, store = _service(
        _Events([event]),
        _Runs(_run()),
        notifier,
        configured=False,
    )
    assert await service.tick() == 0
    assert notifier.reviews == []
    assert store.saved == []


@pytest.mark.asyncio
async def test_missing_carousel_counts_a_failure() -> None:
    event = _event(EVENT_TYPE_READY_FOR_OWNER, {"revision": 2})
    run = _run()
    run = AutopilotRun(
        run_id=run.run_id,
        topic_candidate_id=run.topic_candidate_id,
        carousel_project_id=None,
        state=run.state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    notifier = _Notifier()
    service, store = _service(
        _Events([event]), _Runs(run), notifier, facts=_Facts(facts=None)
    )
    assert await service.tick() == 0
    assert notifier.reviews == []
    assert store.saved[0].log.attempts[0].count == 1


@pytest.mark.asyncio
async def test_unknown_event_and_missing_run_are_skipped() -> None:
    unknown = _event("content.autopilot.other", {})
    missing = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "failed", "reason": "phase_failed"},
        event_id="gone",
    )
    notifier = _Notifier()
    service, store = _service(_Events([unknown, missing]), _Runs(None), notifier)
    assert await service.tick() == 0
    assert notifier.statuses == []
    assert store.saved == []


@pytest.mark.asyncio
async def test_batch_cap_skips_the_reminder_pass() -> None:
    events = [
        _event(
            EVENT_TYPE_STATE_CHANGED,
            {"state": "failed", "reason": "phase_failed"},
            event_id=f"evt-{index}",
        )
        for index in range(NOTIFY_BATCH + 1)
    ]
    notifier = _Notifier()
    service, _store = _service(
        _Events(events),
        _Runs(_run(state=AutopilotRunState.FAILED)),
        notifier,
    )
    assert await service.tick() == NOTIFY_BATCH
    assert len(notifier.statuses) == NOTIFY_BATCH


@pytest.mark.asyncio
async def test_review_and_status_errors_do_not_drop_rate_limits() -> None:
    review = _event(EVENT_TYPE_READY_FOR_OWNER, {"project_id": _PROJECT, "revision": 1})
    status = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "failed", "reason": "phase_failed"},
        event_id="status-1",
    )
    unconfigured = _Notifier(
        error=NotifierUnconfiguredError("autopilot_notifier_unconfigured")
    )
    service, store = _service(_Events([review]), _Runs(_run()), unconfigured)
    assert await service.tick() == 0
    assert store.saved == []
    failed = _Notifier(error=TelegramDeliveryError("telegram_http_500"))
    service, store = _service(_Events([review]), _Runs(_run()), failed)
    assert await service.tick() == 0
    assert store.saved[0].log.attempts[0].count == 1
    quiet = _Notifier(
        error=NotifierUnconfiguredError("autopilot_notifier_unconfigured")
    )
    service, store = _service(
        _Events([status]),
        _Runs(_run(state=AutopilotRunState.FAILED)),
        quiet,
    )
    assert await service.tick() == 0
    assert store.saved == []
    limited = _Notifier(error=TelegramRateLimitedError("telegram_rate_limited"))
    service, store = _service(
        _Events([status]),
        _Runs(_run(state=AutopilotRunState.FAILED)),
        limited,
    )
    assert await service.tick() == 0
    assert store.saved == []


@pytest.mark.asyncio
async def test_reminder_errors_and_a_full_room() -> None:
    updated = _NOW - timedelta(hours=REMINDER_AFTER_HOURS, minutes=1)
    due = _run(updated_at=updated)
    notifier = _Notifier(error=TelegramDeliveryError("telegram_http_500"))
    service, store = _service(_Events([]), _Runs(due), notifier)
    assert await service.tick() == 0
    assert store.saved[0].log.attempts[0].count == 1
    limited = _Notifier(error=TelegramRateLimitedError("telegram_rate_limited"))
    service, store = _service(_Events([]), _Runs(due), limited)
    assert await service.tick() == 0
    assert store.saved == []
    quiet = _Notifier(
        error=NotifierUnconfiguredError("autopilot_notifier_unconfigured")
    )
    service, store = _service(_Events([]), _Runs(due), quiet)
    assert await service.tick() == 0
    assert store.saved == []
    second = _run(updated_at=updated)
    held = _Events([
        _event(
            EVENT_TYPE_STATE_CHANGED,
            {"state": "failed", "reason": "phase_failed"},
            event_id=f"fill-{index}",
        )
        for index in range(NOTIFY_BATCH - 1)
    ])
    service, _store = _service(
        held,
        _Runs(_run(state=AutopilotRunState.FAILED), extra=[due, second]),
        _Notifier(),
    )
    assert await service.tick() == NOTIFY_BATCH


@pytest.mark.asyncio
async def test_blank_chat_and_missing_clock_skip_delivery() -> None:
    event = _event(EVENT_TYPE_READY_FOR_OWNER, {"project_id": _PROJECT, "revision": 1})
    notifier = _Notifier()
    service, store = _service(
        _Events([event]),
        _Runs(_run()),
        notifier,
        chat_id="  ",
    )
    assert await service.tick() == 0
    assert store.saved == []
    waiting = _run(updated_at=None)
    service, store = _service(_Events([]), _Runs(waiting), _Notifier())
    assert await service.tick() == 0
    assert store.saved == []


@pytest.mark.asyncio
async def test_already_recorded_status_is_not_resent() -> None:
    event = _event(
        EVENT_TYPE_STATE_CHANGED,
        {"state": "failed", "reason": "phase_failed"},
    )
    log = NoticeLog(statuses=("evt-1",))
    notifier = _Notifier()
    service, store = _service(
        _Events([event]),
        _Runs(_run(state=AutopilotRunState.FAILED, log=log)),
        notifier,
    )
    assert await service.tick() == 0
    assert notifier.statuses == []
    assert store.saved == []
