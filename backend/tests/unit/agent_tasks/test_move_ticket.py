"""Tests for move_ticket dev-summary auto-scaffold (AE-0169) + board I/O (AE-0237)."""

from pathlib import Path

import pytest
from scripts.agent_tasks import board_io, move_ticket, schema
from scripts.agent_tasks.constants import (
    BOARD_COLUMNS,
    REPORT_DEV_SUFFIX,
    STATUS_REVIEW,
    TASKS_DIR,
)
from scripts.agent_tasks.schema import can_transition, parse_ticket


def _a_ticket():
    ticket = parse_ticket(TASKS_DIR / "AE-0001-agentic-delivery-system.md")
    assert ticket is not None
    return ticket


def test_scaffold_dev_summary_creates_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(move_ticket, "REPORTS_DIR", tmp_path)
    ticket = _a_ticket()

    created = move_ticket.scaffold_dev_summary(ticket)

    assert created is not None
    assert created == tmp_path / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
    body = created.read_text(encoding="utf-8")
    assert ticket.ticket_id in body
    # Required sections the developer must fill before Review.
    for section in (
        "Acceptance Criteria Implemented",
        "Files Changed",
        "Tests Run",
        "Deviations",
        "QA Outcome",
    ):
        assert section in body


def test_scaffold_dev_summary_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(move_ticket, "REPORTS_DIR", tmp_path)
    ticket = _a_ticket()
    report = tmp_path / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
    report.write_text("HAND-WRITTEN — do not clobber", encoding="utf-8")

    result = move_ticket.scaffold_dev_summary(ticket)

    assert result is None
    assert report.read_text(encoding="utf-8") == "HAND-WRITTEN — do not clobber"


def test_unfilled_scaffold_is_rejected_at_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # AE-0166 QA fix: an auto-scaffolded (unfilled) dev-summary must NOT satisfy
    # the Review gate just by existing — the developer has to replace it.
    monkeypatch.setattr(move_ticket, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(schema, "REPORTS_DIR", tmp_path)
    ticket = _a_ticket()
    qa_report = tmp_path / f"{ticket.ticket_id}.qa.md"
    qa_report.write_text("qa", encoding="utf-8")

    move_ticket.scaffold_dev_summary(ticket)
    errors = can_transition(ticket, STATUS_REVIEW)

    assert any("unfilled scaffold" in e for e in errors), errors


def test_filled_dev_summary_passes_scaffold_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(schema, "REPORTS_DIR", tmp_path)
    ticket = _a_ticket()
    (tmp_path / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}").write_text(
        "## Developer Completion Report\nReal, hand-written content.\n",
        encoding="utf-8",
    )
    (tmp_path / f"{ticket.ticket_id}.qa.md").write_text("qa", encoding="utf-8")

    errors = can_transition(ticket, STATUS_REVIEW)

    assert not any("scaffold" in e for e in errors), errors


def test_update_board_with_board_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    board = tmp_path / "BOARD.md"
    monkeypatch.setattr(move_ticket, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(board_io, "load_tickets", lambda _d: [])
    board.write_text(board_io.render_board_text(tasks_dir), encoding="utf-8")

    move_ticket.update_board(board, "AE-0055", STATUS_REVIEW)

    content = board.read_text(encoding="utf-8")
    section = content.split(f"## {STATUS_REVIEW}\n\n", 1)[1]
    assert section.startswith("- AE-0055")


# Seeded-regression proof (AE-0237): moving a ticket when BOARD.md is absent must
# regenerate the board, not raise FileNotFoundError (the FC-1 crash).
def test_update_board_regenerates_when_board_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "AE-0077-example.md").write_text(
        f"# AE-0077 — Example\n\nStatus: {STATUS_REVIEW}\nTier: T2\n",
        encoding="utf-8",
    )
    board = tmp_path / "BOARD.md"
    assert not board.exists()
    monkeypatch.setattr(move_ticket, "TASKS_DIR", tasks_dir)

    move_ticket.update_board(board, "AE-0077", STATUS_REVIEW)

    content = board.read_text(encoding="utf-8")
    assert "- AE-0077" in content
    for column in BOARD_COLUMNS:
        assert f"## {column}" in content
    assert list(tmp_path.glob(".board-*.tmp")) == []


def test_template_has_no_unfilled_format_placeholders() -> None:
    # The template id placeholder must be substituted, not left literal.
    assert "__TICKET_ID__" in move_ticket.DEV_SUMMARY_TEMPLATE
    rendered = move_ticket.DEV_SUMMARY_TEMPLATE.replace("__TICKET_ID__", "AE-9999")
    assert "__TICKET_ID__" not in rendered
    assert "Ticket: AE-9999" in rendered
