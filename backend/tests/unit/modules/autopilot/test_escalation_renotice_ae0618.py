"""The re-notify event's kind, eligibility and ledger marker. Pure.

Feature: tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.dead_letter import dead_letter_keyboard
from rag_backend.modules.autopilot.domain.escalation_renotice import (
    mark_renoticed,
    renotice_due,
    renotice_payload,
)
from rag_backend.modules.autopilot.domain.messages import notice_kind
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog, record_status
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
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


def test_the_marker_makes_a_run_not_due_and_keeps_the_ledger() -> None:
    """Scenario: A second scan sends nothing"""
    log = record_status(NoticeLog(), "earlier", 7)
    run = _run()
    marked = mark_renoticed(log)
    assert marked.statuses == ("earlier", RENOTICE_KEY)
    assert marked.message_ids == (7,)
    assert RENOTICE_KEY == "scan_renotified"
    assert not renotice_due(_with_log(run, marked))


def test_any_other_status_leaves_a_run_due() -> None:
    assert renotice_due(_with_log(_run(), record_status(NoticeLog(), "earlier", 7)))


def _with_log(run: AutopilotRun, log: NoticeLog) -> AutopilotRun:
    from dataclasses import replace

    return replace(run, notice_log=log)


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


def test_a_parked_run_keeps_its_own_buttons() -> None:
    """Scenario: A run the queue parked keeps its own buttons"""
    run = _run(reason="queue_dead_letter:run_budget_exhausted")
    keyboard = status_keyboard(KIND_ESCALATED, run.run_id, renotice_payload(run))
    assert keyboard == dead_letter_keyboard(run.run_id)
