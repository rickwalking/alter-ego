"""Queue position, start estimate, dead-letter notice and queue callbacks. Pure.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogWindow,
    GenerateNowCommand,
    NoBacklog,
    backlog_room,
    expiry_cutoff,
)
from rag_backend.modules.autopilot.domain.dead_letter import (
    dead_letter_keyboard,
    is_parked_notice,
    status_body,
)
from rag_backend.modules.autopilot.domain.messages import StatusCopy
from rag_backend.modules.autopilot.domain.queue_callback import parse_queue_callback
from rag_backend.modules.autopilot.domain.queue_position import (
    QueueSnapshot,
    average_drive_minutes,
    position_of,
    position_text,
)
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
from rag_backend.modules.autopilot.notify_constants import (
    KIND_ESCALATED,
    KIND_FAILED,
    KIND_PUBLISH_FAILED,
)
from rag_backend.modules.autopilot.queue_constants import (
    BUTTON_DEAD_DISCARD,
    BUTTON_DEAD_RETRY,
    DEFAULT_DRIVE_MINUTES,
    KIND_DEAD_RETRY,
    KIND_GENERATE_NOW,
)

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
_DEAD = "queue_dead_letter:phase_budget_exhausted"


def _copy(reason: str) -> StatusCopy:
    return StatusCopy(reason=reason, link="", permalink="", days_remaining=None)


def test_the_position_counts_the_runs_ahead_in_fifo_order() -> None:
    """Scenario: The position counts the runs ahead in FIFO order"""
    older, newer = uuid4(), uuid4()
    snapshot = QueueSnapshot(ahead=("running", None), waiting=(str(older), str(newer)))
    first = position_of(snapshot, older, _NOW)
    second = position_of(snapshot, newer, _NOW)
    assert first is not None
    assert second is not None
    assert (first.position, first.total) == (3, 4)
    assert (second.position, second.total) == (4, 4)
    assert position_of(snapshot, uuid4(), _NOW) is None


def test_the_start_estimate_uses_recent_drive_times() -> None:
    """Scenario: The start estimate uses recent drive times"""
    run_id = uuid4()
    snapshot = QueueSnapshot(
        ahead=("a", "b"), waiting=(str(run_id),), drive_minutes=(10.0, 20.0)
    )
    position = position_of(snapshot, run_id, _NOW)
    assert position is not None
    assert position.eta == _NOW + timedelta(minutes=30)
    assert average_drive_minutes(()) == DEFAULT_DRIVE_MINUTES
    no_history = position_of(
        QueueSnapshot(ahead=("a",), waiting=(str(run_id),)), run_id, _NOW
    )
    assert no_history is not None
    assert no_history.eta == _NOW + timedelta(minutes=DEFAULT_DRIVE_MINUTES)


def test_the_position_text_is_in_sao_paulo_time() -> None:
    """Scenario: Confirmar shows the queue position and the estimated start"""
    run_id = uuid4()
    position = position_of(
        QueueSnapshot(ahead=("a",), waiting=(str(run_id),), drive_minutes=(30.0,)),
        run_id,
        _NOW,
    )
    assert position is not None
    assert position_text(position) == (
        "Na fila: posição 2 de 2 — início estimado 11:30."
    )


def test_a_dead_lettered_run_shows_retry_and_discard() -> None:
    """Scenario: A dead-lettered run shows Retry and Discard"""
    run_id = uuid4()
    for kind in (KIND_ESCALATED, KIND_FAILED):
        assert is_parked_notice(kind, _DEAD)
        body = status_body(kind, _copy(_DEAD))
        assert body.startswith("⚠️ A fila parou este carrossel:")
        assert "memória" in body
        keyboard = status_keyboard(kind, run_id, {"reason": _DEAD})
        assert keyboard == dead_letter_keyboard(run_id)
    buttons = dead_letter_keyboard(run_id).rows[0]
    assert [b.text for b in buttons] == [BUTTON_DEAD_RETRY, BUTTON_DEAD_DISCARD]
    assert [b.callback_data for b in buttons] == [
        f"ap:qrt:{run_id}",
        f"ap:qdc:{run_id}",
    ]
    assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert "(mystery)" in status_body(
        KIND_ESCALATED, _copy("queue_dead_letter:mystery")
    )


def test_other_notices_keep_their_text_and_buttons() -> None:
    """Scenario: Retry is refused for an escalation that is not a queue dead letter"""
    run_id = uuid4()
    assert not is_parked_notice(KIND_ESCALATED, "engine_error:RuntimeError")
    assert not is_parked_notice(KIND_PUBLISH_FAILED, _DEAD)
    assert status_keyboard(KIND_ESCALATED, run_id, {"reason": "engine_error:X"}) is None
    assert status_body(KIND_ESCALATED, _copy("engine_error:X")).startswith("Escalated")


def test_queue_callbacks_parse_and_others_do_not() -> None:
    """Scenario: "Gerar agora" queues a backlog theme at once, outside the daily cap"""
    target = uuid4()
    retry = parse_queue_callback(f"ap:qrt:{target}")
    now = parse_queue_callback(f"ap:qnow:{target}")
    assert retry is not None
    assert now is not None
    assert (retry.kind, retry.target) == (KIND_DEAD_RETRY, target)
    assert (now.kind, now.target) == (KIND_GENERATE_NOW, target)
    assert parse_queue_callback(f"ap:thok:{target}") is None
    assert parse_queue_callback("ap:qrt:not-a-uuid") is None


async def test_an_unwired_backlog_holds_nothing() -> None:
    """Scenario: Themes over the daily cap wait in the backlog"""
    empty = NoBacklog()
    window = BacklogWindow(since=_NOW - timedelta(days=7), before=_NOW)
    command = GenerateNowCommand(candidate_id=uuid4(), run_id=uuid4(), created_at=_NOW)
    assert await empty.waiting(window) == []
    assert await empty.unannounced() == []
    assert await empty.generate_now(command) is None
    moved = await empty.change(BacklogChange(candidate_ids=(uuid4(),), status="x"))
    assert moved == ()
    assert backlog_room(waiting_count=12, promoted=1) == 0
    assert backlog_room(waiting_count=4, promoted=2) == 8
    assert expiry_cutoff(_NOW) == _NOW - timedelta(days=7)
