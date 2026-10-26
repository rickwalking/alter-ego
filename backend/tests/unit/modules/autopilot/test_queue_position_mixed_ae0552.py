"""Mixed staged/unstaged queue order and retry-aware ETAs share one pure core."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.domain.queue_board import (
    BoardInputs,
    BoardItem,
    GenerationRow,
    build_board,
)
from rag_backend.modules.autopilot.domain.queue_position import (
    QueueEntry,
    QueueSnapshot,
    position_of,
    queue_placements,
)

_NOW = datetime(2026, 10, 25, 14, 0, tzinfo=UTC)
_CREATED = _NOW - timedelta(hours=1)


def _entry(entry_id: str, status: str, created_at: datetime) -> QueueEntry:
    return QueueEntry(
        id=entry_id,
        status=status,
        autopilot_run_id=entry_id,
        created_at=created_at,
    )


def _row(entry: QueueEntry) -> GenerationRow:
    return GenerationRow(
        id=entry.id,
        kind="autopilot_drive",
        status=entry.status,
        autopilot_run_id=entry.autopilot_run_id,
        carousel_project_id=None,
        title=entry.id,
        last_phase=None,
        last_error_code=None,
        created_at=entry.created_at,
        started_at=entry.started_at,
        next_attempt_at=entry.next_attempt_at,
        finished_at=None,
        pgq_job_id=entry.pgq_job_id,
        priority=entry.priority,
        staged=entry.staged,
    )


def _board(entries: list[QueueEntry]) -> tuple[BoardItem, ...]:
    board = build_board(
        BoardInputs(
            rows=[_row(entry) for entry in entries],
            facts={},
            backlog=[],
            drive_minutes=[20.0],
            now=_NOW,
        )
    )
    return board.active


def _mixed_entries(target: UUID) -> list[QueueEntry]:
    running = replace(_entry("running", "running", _CREATED), pgq_job_id=50)
    manual_job = replace(
        _entry("manual-job", "queued", _CREATED), priority=1, pgq_job_id=30
    )
    manual_new = replace(
        _entry("manual-new", "queued", _CREATED), priority=1, staged=False
    )
    ordinary_late = replace(_entry("ordinary-late", "queued", _CREATED), pgq_job_id=20)
    ordinary_early = replace(
        _entry("ordinary-early", "queued", _CREATED), pgq_job_id=10
    )
    unstaged = replace(
        _entry("unstaged", "queued", _CREATED + timedelta(minutes=1)),
        autopilot_run_id=str(target),
        staged=False,
    )
    return [unstaged, ordinary_late, manual_new, running, ordinary_early, manual_job]


def test_mixed_staged_unstaged_order_matches_telegram() -> None:
    """Scenario: Telegram and the panel share priority order and retry-aware estimates"""
    target = uuid4()
    entries = _mixed_entries(target)
    snapshot = QueueSnapshot(entries=tuple(entries), drive_minutes=(20.0,))
    expected = [
        "running",
        "manual-job",
        "manual-new",
        "ordinary-early",
        "ordinary-late",
        "unstaged",
    ]
    assert [place.entry.id for place in queue_placements(snapshot, _NOW)] == expected
    assert [item.id for item in _board(entries)] == expected
    telegram = position_of(snapshot, target, _NOW)
    panel = _board(entries)[-1]
    assert telegram is not None
    assert (telegram.position, telegram.total) == (6, 6)
    assert (panel.position, panel.eta) == (telegram.position, telegram.eta)


def _retry_entries(target: UUID, next_attempt: datetime) -> list[QueueEntry]:
    running = replace(
        _entry("running", "running", _CREATED), started_at=_NOW - timedelta(minutes=5)
    )
    retry = replace(
        _entry("retry", "retry_wait", _CREATED - timedelta(minutes=1)),
        next_attempt_at=next_attempt,
    )
    queued = replace(
        _entry("queued", "queued", _CREATED),
        autopilot_run_id=str(target),
        staged=False,
    )
    return [queued, retry, running]


def test_retry_rejoin_and_running_elapsed_drive_both_etas() -> None:
    """Scenario: Telegram and the panel share priority order and retry-aware estimates"""
    target = uuid4()
    entries = _retry_entries(target, _NOW + timedelta(minutes=30))
    snapshot = QueueSnapshot(entries=tuple(entries), drive_minutes=(20.0,))
    telegram = position_of(snapshot, target, _NOW)
    panel = _board(entries)
    assert telegram is not None
    assert telegram.eta == _NOW + timedelta(minutes=50)
    assert [(item.id, item.position) for item in panel] == [
        ("running", 1),
        ("retry", None),
        ("queued", 2),
    ]
    assert panel[-1].eta == telegram.eta


def test_undispatched_work_uses_creation_then_run_id_within_its_class() -> None:
    """Scenario: Telegram and the panel share priority order and retry-aware estimates"""
    older = _entry("z-older", "queued", _CREATED - timedelta(minutes=1))
    first_tie = _entry("a-tie", "queued", _CREATED)
    second_tie = _entry("c-tie", "queued", _CREATED)
    newer = _entry("b-newer", "queued", _CREATED + timedelta(minutes=1))
    snapshot = QueueSnapshot(entries=(newer, second_tie, older, first_tie))
    ordered = queue_placements(snapshot, _NOW)
    assert [place.entry.id for place in ordered] == [
        "z-older",
        "a-tie",
        "c-tie",
        "b-newer",
    ]


def test_retry_rejoin_never_moves_an_eta_earlier() -> None:
    """Scenario: Telegram and the panel share priority order and retry-aware estimates"""
    target = uuid4()
    entries = _retry_entries(target, _NOW + timedelta(minutes=5))
    snapshot = QueueSnapshot(entries=tuple(entries), drive_minutes=(20.0,))
    position = position_of(snapshot, target, _NOW)
    assert position is not None
    assert position.eta == _NOW + timedelta(minutes=35)


def test_running_remaining_time_clamps_at_zero() -> None:
    """Scenario: Telegram and the panel share priority order and retry-aware estimates"""
    target = uuid4()
    running = replace(
        _entry("running", "running", _CREATED), started_at=_NOW - timedelta(minutes=30)
    )
    queued = replace(_entry("queued", "queued", _CREATED), autopilot_run_id=str(target))
    snapshot = QueueSnapshot(entries=(queued, running), drive_minutes=(20.0,))
    position = position_of(snapshot, target, _NOW)
    assert position is not None
    assert position.eta == _NOW
