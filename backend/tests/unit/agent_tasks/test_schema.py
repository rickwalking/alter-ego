"""Tests for agent ticket schema validation."""

from pathlib import Path

import pytest
from scripts.agent_tasks.constants import (
    STATUS_IN_DEVELOPMENT,
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


def test_validate_all_real_repo() -> None:
    tickets = load_tickets(TASKS_DIR)
    for ticket in tickets:
        if ticket.status == STATUS_REVIEW:
            pytest.skip("Review tickets need QA artifacts in fixture")
        errors = validate_ticket_file(ticket)
        assert errors == [], f"{ticket.ticket_id}: {errors}"


def test_ae_0001_in_development_valid() -> None:
    path = TASKS_DIR / "AE-0001-agentic-delivery-system.md"
    ticket = parse_ticket(path)
    assert ticket is not None
    assert ticket.status == STATUS_IN_DEVELOPMENT
    errors = can_transition(ticket, STATUS_IN_DEVELOPMENT)
    assert errors == []
