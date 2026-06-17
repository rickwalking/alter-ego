"""Tests for move_ticket dev-summary auto-scaffold (AE-0169)."""

from pathlib import Path

import pytest
from scripts.agent_tasks import move_ticket
from scripts.agent_tasks.constants import REPORT_DEV_SUFFIX, TASKS_DIR
from scripts.agent_tasks.schema import parse_ticket


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


def test_template_has_no_unfilled_format_placeholders() -> None:
    # The template id placeholder must be substituted, not left literal.
    assert "__TICKET_ID__" in move_ticket.DEV_SUMMARY_TEMPLATE
    rendered = move_ticket.DEV_SUMMARY_TEMPLATE.replace("__TICKET_ID__", "AE-9999")
    assert "__TICKET_ID__" not in rendered
    assert "Ticket: AE-9999" in rendered
