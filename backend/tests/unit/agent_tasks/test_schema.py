"""Tests for agent ticket schema validation."""

from pathlib import Path

import pytest
from scripts.agent_tasks.constants import (
    ALL_STATUSES,
    STATUS_DEV_COMPLETE,
    STATUS_INTAKE,
    STATUS_READY,
    STATUS_REVIEW,
    TASKS_DIR,
)
from scripts.agent_tasks.schema import (
    can_transition,
    load_tickets,
    parse_ticket,
    validate_ticket_file,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_parse_ae_0001() -> None:
    path = TASKS_DIR / "AE-0001-agentic-delivery-system.md"
    ticket = parse_ticket(path)
    assert ticket is not None
    assert ticket.ticket_id == "AE-0001"
    assert ticket.tier == "T3"


def test_load_tickets_excludes_templates() -> None:
    tickets = load_tickets(TASKS_DIR)
    ids = {t.ticket_id for t in tickets}
    assert "AE-0001" in ids
    assert all(not t.path.name.startswith("_template") for t in tickets)


def test_ready_transition_requires_sections(tmp_path: Path) -> None:
    content = """# AE-9999 — Test

Status: Intake
Tier: T2

## Goal
Do something.

## Problem
Because.

## Scope
- A

## Non-Goals
- B

## Acceptance Criteria
- [ ] AC1
"""
    path = tmp_path / "AE-9999-test.md"
    path.write_text(content, encoding="utf-8")
    ticket = parse_ticket(path)
    assert ticket is not None
    errors = can_transition(ticket, STATUS_READY)
    assert errors == []


def test_ready_fails_without_acceptance_criteria(tmp_path: Path) -> None:
    content = """# AE-9998 — Test

Status: Intake
Tier: T2

## Goal
x

## Problem
y

## Scope
z

## Non-Goals
w

## Acceptance Criteria
Pending.
"""
    path = tmp_path / "AE-9998-test.md"
    path.write_text(content, encoding="utf-8")
    ticket = parse_ticket(path)
    assert ticket is not None
    errors = can_transition(ticket, STATUS_READY)
    assert any("acceptance" in e.lower() for e in errors)


def test_review_requires_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = """# AE-9997 — Test

Status: Dev Complete
Tier: T2

## Goal
g

## Problem
p

## Scope
s

## Non-Goals
n

## Acceptance Criteria
- [x] done

## Test Evidence
```bash
pytest
```
"""
    path = tmp_path / "AE-9997-test.md"
    path.write_text(content, encoding="utf-8")
    ticket = parse_ticket(path)
    assert ticket is not None
    monkeypatch.setattr(
        "scripts.agent_tasks.schema.REPORTS_DIR",
        tmp_path / "reports",
    )
    errors = can_transition(ticket, STATUS_REVIEW)
    assert len(errors) >= 2


def _review_ticket(tmp_path: Path) -> Path:
    content = """# AE-9996 — Test

Status: Dev Complete
Tier: T2

## Goal
g

## Problem
p

## Scope
s

## Non-Goals
n

## Acceptance Criteria
- [x] done

## Test Evidence
```bash
pytest
```
"""
    path = tmp_path / "AE-9996-test.md"
    path.write_text(content, encoding="utf-8")
    return path


# AE-0181 — Feature: existence-only QA-report gate hardened to content + attribution
#   Scenario: a real, attributed QA report satisfies the Review gate
def test_review_passes_with_attributed_qa_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("scripts.agent_tasks.schema.REPORTS_DIR", reports)
    (reports / "AE-9996.dev-summary.md").write_text(
        "# Dev Summary\nTicket: AE-9996\nReal content here.\n", encoding="utf-8"
    )
    (reports / "AE-9996.qa.md").write_text(
        "# QA Validation Report — AE-9996\n\n## Overall Score: 90\nReal QA content.\n",
        encoding="utf-8",
    )
    assert can_transition(ticket, STATUS_REVIEW) == []


#   Scenario: an EMPTY/placeholder QA report must NOT vacuously pass
def test_review_fails_on_empty_qa_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("scripts.agent_tasks.schema.REPORTS_DIR", reports)
    (reports / "AE-9996.dev-summary.md").write_text(
        "# Dev Summary\nTicket: AE-9996\nReal content.\n", encoding="utf-8"
    )
    (reports / "AE-9996.qa.md").write_text("\n\n", encoding="utf-8")  # empty
    errors = can_transition(ticket, STATUS_REVIEW)
    assert any("empty or a placeholder" in e for e in errors)


#   Scenario: a QA report authored for ANOTHER ticket (same slot) must not freeload
def test_review_fails_on_unattributed_qa_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("scripts.agent_tasks.schema.REPORTS_DIR", reports)
    (reports / "AE-9996.dev-summary.md").write_text(
        "# Dev Summary\nTicket: AE-9996\nReal content.\n", encoding="utf-8"
    )
    # Report content names a DIFFERENT ticket — it must not satisfy AE-9996.
    (reports / "AE-9996.qa.md").write_text(
        "# QA Validation Report — AE-1234\n\n## Overall Score: 90\nQA for 1234.\n",
        encoding="utf-8",
    )
    errors = can_transition(ticket, STATUS_REVIEW)
    assert any("not attributed to AE-9996" in e for e in errors)


#   Scenario: a dev-summary authored for ANOTHER ticket must not freeload either
def test_dev_complete_fails_on_unattributed_dev_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("scripts.agent_tasks.schema.REPORTS_DIR", reports)
    # Dev-summary body names a different ticket (no "AE-9996").
    (reports / "AE-9996.dev-summary.md").write_text(
        "# Dev Summary\nTicket: AE-1234\nWork for a different ticket.\n",
        encoding="utf-8",
    )
    errors = validate_ticket_file(ticket)
    assert any("not attributed to AE-9996" in e for e in errors)


def test_validate_all_real_repo() -> None:
    tickets = load_tickets(TASKS_DIR)
    for ticket in tickets:
        if ticket.status == STATUS_REVIEW:
            pytest.skip("Review tickets need QA artifacts in fixture")
        errors = validate_ticket_file(ticket)
        assert errors == [], f"{ticket.ticket_id}: {errors}"


def test_ae_0001_dev_complete_valid() -> None:
    path = TASKS_DIR / "AE-0001-agentic-delivery-system.md"
    ticket = parse_ticket(path)
    assert ticket is not None
    assert ticket.status == STATUS_DEV_COMPLETE
    errors = validate_ticket_file(ticket)
    assert errors == []


def test_invalid_status_message_is_self_documenting(tmp_path: Path) -> None:
    # AE-0222: a wrong status (e.g. "Todo") must not just say "Invalid status";
    # the error has to list the valid options and name the entry state so the
    # author can fix it without reading constants.py.
    content = """# AE-9999 — Test

Status: Todo
Tier: T2

## Acceptance Criteria
- [ ] AC1
"""
    path = tmp_path / "AE-9999-test.md"
    path.write_text(content, encoding="utf-8")
    ticket = parse_ticket(path)
    assert ticket is not None

    errors = validate_ticket_file(ticket)
    assert len(errors) == 1
    message = errors[0]
    assert message.startswith("Invalid status: Todo")
    # Lists every valid status and names the entry state.
    for status in ALL_STATUSES:
        assert status in message
    assert f"'{STATUS_INTAKE}'" in message
    assert "T0-only" in message


def test_can_transition_to_unknown_status_is_self_documenting() -> None:
    ticket = parse_ticket(TASKS_DIR / "AE-0001-agentic-delivery-system.md")
    assert ticket is not None
    errors = can_transition(ticket, "Nonsense")
    assert len(errors) == 1
    assert errors[0].startswith("Invalid status: Nonsense")
    assert STATUS_INTAKE in errors[0]
