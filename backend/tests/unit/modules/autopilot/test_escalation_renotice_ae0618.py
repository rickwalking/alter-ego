"""The re-notify event's kind, eligibility and ledger marker. Pure.

Feature: tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.escalation_renotice import (
    PastNotice,
    carried_retry,
    claim_send,
    mark_renoticed,
    release_send,
    renotice_due,
    renotice_payload,
    send_claimed,
)
from rag_backend.modules.autopilot.domain.messages import notice_kind
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    bump_attempt,
    record_status,
)
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
from rag_backend.modules.autopilot.infrastructure.escalation_renotice import _mapping
from rag_backend.modules.autopilot.notify_constants import (
    EVENT_TYPE_ESCALATION_RENOTICE,
    KIND_ESCALATED,
    NOTIFY_EVENT_TYPES,
)
from rag_backend.modules.autopilot.renotice_constants import (
    CAROUSEL_RETRY_SHIPPED_AT,
    RENOTICE_KEY,
)

_S = AutopilotRunState


def _run(
    state: _S = _S.ESCALATED,
    reason: str | None = "persona_score_below_threshold",
    project: str | None = "project",
) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=project,
        state=state,
        state_reason=reason,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


def test_retry_shipped_at_is_the_end_of_the_deploy_of_retry() -> None:
    assert datetime(2026, 11, 4, 9, 21, 21, tzinfo=UTC) == CAROUSEL_RETRY_SHIPPED_AT


def test_the_notifier_reads_the_event_as_an_escalation() -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    assert EVENT_TYPE_ESCALATION_RENOTICE == "content.autopilot.escalation_renotice"
    assert EVENT_TYPE_ESCALATION_RENOTICE in NOTIFY_EVENT_TYPES
    kind = notice_kind(EVENT_TYPE_ESCALATION_RENOTICE, {"state": "failed"})
    assert kind == KIND_ESCALATED


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
def test_a_stuck_run_is_due(state: _S) -> None:
    assert renotice_due(_run(state))


def test_a_run_with_no_reason_is_due() -> None:
    assert renotice_due(_run(reason=None))


@pytest.mark.parametrize(
    "state",
    [state for state in _S if state not in {_S.ESCALATED, _S.FAILED}],
)
def test_a_run_in_any_other_state_is_not_due(state: _S) -> None:
    """Scenario: A run in any other state is skipped"""
    assert not renotice_due(_run(state))


def test_a_run_with_no_carousel_is_not_due() -> None:
    """Scenario: A run with no carousel is skipped"""
    assert not renotice_due(_run(project=None))
    assert not renotice_due(_run(project=""))


@pytest.mark.parametrize(
    "reason",
    [
        "owner_queue_cancelled",
        "owner_queue_discard",
        "owner_queue_retry",
        "queue_daily_recovery",
    ],
)
def test_a_run_closed_by_the_owner_or_a_retry_is_not_due(reason: str) -> None:
    """Scenario: A run closed by the owner or by a retry is skipped"""
    assert not renotice_due(_run(_S.FAILED, reason))


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
def test_a_parked_run_is_not_due(state: _S) -> None:
    """Scenario Outline: A run the queue parked is skipped"""
    assert not renotice_due(_run(state, "queue_dead_letter:run_budget_exhausted"))


def test_the_marker_names_its_event_and_keeps_the_ledger() -> None:
    """Scenario: A second scan sends nothing"""
    marked = mark_renoticed(record_status(NoticeLog(), "earlier", 7), "e1")
    assert marked.statuses == ("earlier", "scan_renotified:e1")
    assert marked.message_ids == (7,)
    assert RENOTICE_KEY == "scan_renotified"


def test_a_notice_still_waiting_keeps_a_run_not_due() -> None:
    """Scenario: A notice still waiting in the outbox is not emitted again"""
    assert not renotice_due(_with_log(_run(), mark_renoticed(NoticeLog(), "e1")))


def test_a_delivered_notice_keeps_a_run_not_due_even_after_failures() -> None:
    """Scenario: A second scan sends nothing"""
    log = _attempts(mark_renoticed(NoticeLog(), "e1"), "e1", 3)
    assert not renotice_due(_with_log(_run(), record_status(log, "e1", 7)))


def test_a_notice_with_attempts_left_keeps_a_run_not_due() -> None:
    """Scenario: A notice still being retried is not queued again"""
    log = _attempts(mark_renoticed(NoticeLog(), "e1"), "e1", 2)
    assert not renotice_due(_with_log(_run(), log))


def test_a_notice_given_up_on_makes_a_run_due_again() -> None:
    """Scenario: A notice the notifier gave up on gets another chance on the next scan"""
    log = _attempts(mark_renoticed(NoticeLog(), "e1"), "e1", 3)
    assert renotice_due(_with_log(_run(), log))


def test_a_claimed_notice_keeps_a_run_not_due_even_when_exhausted() -> None:
    """Scenario: A send with an unknown outcome is never repeated"""
    log = _attempts(mark_renoticed(NoticeLog(), "e1"), "e1", 3)
    assert not renotice_due(_with_log(_run(), claim_send(log, "e1")))


def test_every_queued_notice_must_be_given_up_on() -> None:
    """Scenario: A notice that keeps failing is queued once per scan"""
    first = _attempts(mark_renoticed(NoticeLog(), "e1"), "e1", 3)
    second = mark_renoticed(first, "e2")
    assert not renotice_due(_with_log(_run(), second))
    assert renotice_due(_with_log(_run(), _attempts(second, "e2", 3)))


def test_the_claim_is_held_until_released() -> None:
    """Scenario: A send with an unknown outcome is never repeated"""
    log = claim_send(NoticeLog(), "e1")
    assert log.statuses == ("scan_renotice_sending:e1",)
    assert send_claimed(log, "e1")
    assert not send_claimed(log, "e2")
    assert not send_claimed(release_send(log, "e1"), "e1")
    assert claim_send(log, "e2").statuses == (
        "scan_renotice_sending:e1",
        "scan_renotice_sending:e2",
    )


def test_any_other_status_leaves_a_run_due() -> None:
    assert renotice_due(_with_log(_run(), record_status(NoticeLog(), "earlier", 7)))


def _with_log(run: AutopilotRun, log: NoticeLog) -> AutopilotRun:
    return replace(run, notice_log=log)


def _attempts(log: NoticeLog, event_id: str, count: int) -> NoticeLog:
    for _ in range(count):
        log = bump_attempt(log, f"status:{event_id}")
    return log


def test_the_payload_carries_the_state_and_reason() -> None:
    assert renotice_payload(_run(_S.FAILED, "phase_failed")) == {
        "state": "failed",
        "reason": "phase_failed",
    }


def test_the_payload_of_a_run_with_no_reason_names_its_state() -> None:
    assert renotice_payload(_run(reason=None))["reason"] == "escalated"


def test_the_notice_carries_the_carousel_retry() -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run = _run()
    keyboard = status_keyboard(KIND_ESCALATED, run.run_id, renotice_payload(run))
    assert keyboard == carousel_retry_keyboard(run.run_id)


def test_a_failed_run_also_gets_the_carousel_retry() -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    run = _run(_S.FAILED, "phase_failed")
    keyboard = status_keyboard(KIND_ESCALATED, run.run_id, renotice_payload(run))
    assert keyboard == carousel_retry_keyboard(run.run_id)


_PARKED = "queue_dead_letter:run_budget_exhausted"
_STATE_CHANGED = "content.autopilot.state_changed"
_PUBLISH = "content.autopilot.publish_notice"
_FAILED_PUBLISH = {"outcome": "publish_failed", "error_code": "ig_error"}


def _past(
    event_type: str, payload: dict[str, object], *, since_retry: bool = False
) -> PastNotice:
    return PastNotice(
        run_id=uuid4(),
        event_type=event_type,
        payload=payload,
        since_retry=since_retry,
    )


@pytest.mark.parametrize("state", ["escalated", "failed"])
@pytest.mark.parametrize("since_retry", [False, True])
def test_a_parked_notice_carried_retry_at_any_date(
    state: str, *, since_retry: bool
) -> None:
    """Scenario Outline: A run parked earlier is skipped whatever its reason is now"""
    payload: dict[str, object] = {"state": state, "reason": _PARKED}
    assert carried_retry(_past(_STATE_CHANGED, payload, since_retry=since_retry))


def test_an_escalation_carried_retry_only_since_retry_shipped() -> None:
    """Scenario: A run already notified with Retry is skipped"""
    payload: dict[str, object] = {"state": "escalated", "reason": "phase_failed"}
    assert carried_retry(_past(_STATE_CHANGED, payload, since_retry=True))
    assert not carried_retry(_past(_STATE_CHANGED, payload))


@pytest.mark.parametrize("since_retry", [False, True])
def test_a_failed_notice_carried_no_retry(*, since_retry: bool) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    payload: dict[str, object] = {"state": "failed", "reason": "phase_failed"}
    assert not carried_retry(_past(_STATE_CHANGED, payload, since_retry=since_retry))


def test_a_publish_failure_that_offered_retry_counts_at_any_date() -> None:
    """Scenario: A failed publish notice that offered Retry counts"""
    assert carried_retry(_past(_PUBLISH, _FAILED_PUBLISH))


def test_a_publish_failure_with_no_retry_does_not_count() -> None:
    """Scenario: A failed publish notice with no Retry does not count"""
    payload: dict[str, object] = {**_FAILED_PUBLISH, "offer_retry": False}
    assert not carried_retry(_past(_PUBLISH, payload))


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        (_STATE_CHANGED, {}),
        (_STATE_CHANGED, {"state": "awaiting_owner", "reason": "rework_retry"}),
        (_PUBLISH, {"outcome": "published"}),
        ("content.autopilot.other", {"state": "escalated"}),
    ],
)
def test_any_other_notice_carried_no_retry(
    event_type: str, payload: dict[str, object]
) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    assert not carried_retry(_past(event_type, payload, since_retry=True))


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"state": "escalated"}, {"state": "escalated"}),
        ({}, {}),
        (["escalated"], {}),
        (None, {}),
    ],
)
def test_only_a_mapping_payload_is_read(
    payload: object, expected: dict[str, object]
) -> None:
    """Scenario: A run already notified with Retry is skipped"""
    assert _mapping(payload) == expected
