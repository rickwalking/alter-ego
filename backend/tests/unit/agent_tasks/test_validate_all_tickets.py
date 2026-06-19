"""Seeded-violation tests for the blocking duplicate-ID gate (AE-0238).

AE-0181 made duplicate AE-#### ids a non-blocking WARNING; two real collisions
(AE-0145..0148 → AE-0224..0227, plus an AE-0228 near-miss) promoted it to a hard
gate. These tests pin the exact 0→1 exit-code boundary the cold-critic flagged:
two same-id files with NO other validation errors must fail (exit 1), and a
unique-id control must still pass (exit 0). Tests monkeypatch TASKS_DIR to
`tmp_path` — they never touch the real `.agent/tasks/` tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.agent_tasks import validate_all_tickets
from scripts.agent_tasks.schema import load_tickets


def _write_ticket(tasks_dir: Path, filename: str, ticket_id: str) -> None:
    (tasks_dir / filename).write_text(
        f"# {ticket_id} — Example\n\nStatus: Intake\nTier: T2\n",
        encoding="utf-8",
    )


def test_duplicate_ids_fail_with_no_other_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_ticket(tmp_path, "AE-0500-one.md", "AE-0500")
    _write_ticket(tmp_path, "AE-0500-two.md", "AE-0500")
    monkeypatch.setattr(validate_all_tickets, "TASKS_DIR", tmp_path)

    # Precondition: the two files are otherwise valid (Intake → no section gate),
    # so the only thing that can flip the exit code is the duplicate id.
    assert all(
        not validate_all_tickets.validate_ticket_file(t)
        for t in load_tickets(tmp_path)
    )

    assert validate_all_tickets.main() == 1


def test_unique_ids_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_ticket(tmp_path, "AE-0500-one.md", "AE-0500")
    _write_ticket(tmp_path, "AE-0501-two.md", "AE-0501")
    monkeypatch.setattr(validate_all_tickets, "TASKS_DIR", tmp_path)

    assert validate_all_tickets.main() == 0
