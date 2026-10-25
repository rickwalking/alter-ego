"""The queue panel's board: order, positions and start estimates. Pure.

Feature: backend/tests/features/queue_board_api_ae0526.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.domain.queue_board import (
    AutopilotFacts,
    BoardInputs,
    GenerationRow,
    build_board,
)

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)


def _row(
    row_id: str, status: str, minutes_ago: int, run: str | None = "r"
) -> GenerationRow:
    return GenerationRow(
        id=row_id,
        kind="autopilot_drive",
        status=status,
        autopilot_run_id=run,
        carousel_project_id=None,
        title="",
        last_phase=None,
        last_error_code=None,
        created_at=_NOW - timedelta(minutes=minutes_ago),
        started_at=None,
        next_attempt_at=None,
        finished_at=None,
    )


def test_the_running_drive_leads_and_queued_ones_get_estimates() -> None:
    """Scenario: The board lists the active runs in FIFO order with positions"""
    board = build_board(
        BoardInputs(
            rows=[
                _row("a", "queued", 30),
                _row("b", "running", 40, run="g"),
                _row("c", "retry_wait", 20, run="g"),
                _row("d", "queued", 10),
            ],
            facts={
                "r": AutopilotFacts(title="Tema", state="queued", state_reason=None),
                "g": AutopilotFacts(
                    title="Rodando", state="generating", state_reason=None
                ),
            },
            backlog=[],
            drive_minutes=[10.0, 30.0],
            now=_NOW,
        )
    )
    assert [item.id for item in board.active] == ["b", "a", "c", "d"]
    assert [item.position for item in board.active] == [1, 2, None, 3]
    assert board.active[0].eta is None
    assert board.active[1].eta == _NOW + timedelta(minutes=20)
    assert board.active[2].eta is None
    assert board.active[3].eta == _NOW + timedelta(minutes=40)
    assert [item.can_cancel for item in board.active] == [False, True, False, True]
    assert board.active[1].title == "Tema"
    assert board.average_drive_minutes == 20.0


def test_a_superseded_dashboard_dead_letter_is_hidden() -> None:
    """Scenario: A parked dashboard resume is listed without buttons"""
    dashboard = GenerationRow(
        id="w",
        kind="workflow_resume",
        status="dead_letter",
        autopilot_run_id=None,
        carousel_project_id="p",
        title="Painel",
        last_phase=None,
        last_error_code="permanent",
        created_at=_NOW,
        started_at=None,
        next_attempt_at=None,
        finished_at=_NOW,
        superseded=True,
    )
    board = build_board(
        BoardInputs(rows=[dashboard], facts={}, backlog=[], drive_minutes=[], now=_NOW)
    )
    assert board.dead == ()


def test_a_dead_letter_without_its_run_is_hidden() -> None:
    """Scenario: A parked autopilot run is listed until it is resolved"""
    board = build_board(
        BoardInputs(
            rows=[_row("x", "dead_letter", 5, run="gone")],
            facts={},
            backlog=[],
            drive_minutes=[],
            now=_NOW,
        )
    )
    assert board.dead == ()
