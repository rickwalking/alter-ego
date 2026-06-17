"""Ticket parsing and transition validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scripts.agent_tasks.constants import (
    ALL_STATUSES,
    DEV_SUMMARY_SCAFFOLD_MARKER,
    FIELD_STATUS,
    FIELD_TIER,
    HOTFIX_MIN_SECTIONS,
    REPORT_DEV_SUFFIX,
    REPORT_QA_SUFFIX,
    REPORTS_DIR,
    REQUIRED_READY_SECTIONS,
    SECTION_ACCEPTANCE_CRITERIA,
    SECTION_FINAL_SUMMARY,
    TIER_T1,
    TIER_T2,
    TIER_T3,
    STATUS_DEV_COMPLETE,
    STATUS_DONE,
    STATUS_IN_DEVELOPMENT,
    STATUS_READY,
    STATUS_REVIEW,
)

TICKET_ID_PATTERN = re.compile(r"^# (AE-\d{4}) —", re.MULTILINE)
STATUS_PATTERN = re.compile(r"^Status:\s*(.+)$", re.MULTILINE)
TIER_PATTERN = re.compile(r"^Tier:\s*(T[0-3])$", re.MULTILINE)


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    path: Path
    status: str
    tier: str
    content: str

    def has_section(self, heading: str) -> bool:
        return heading in self.content

    def section_has_content(self, heading: str) -> bool:
        if heading not in self.content:
            return False
        start = self.content.index(heading) + len(heading)
        rest = self.content[start:]
        next_heading = rest.find("\n## ")
        block = rest[:next_heading] if next_heading != -1 else rest
        stripped = block.strip()
        if not stripped:
            return False
        pending_markers = ("Pending.", "Pending", "TBD", "None.", "None")
        lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
        if not lines:
            return False
        if all(any(ln.startswith(m) for m in pending_markers) for ln in lines):
            return False
        return True

    def has_acceptance_criteria(self) -> bool:
        if SECTION_ACCEPTANCE_CRITERIA not in self.content:
            return False
        start = self.content.index(SECTION_ACCEPTANCE_CRITERIA)
        rest = self.content[start:]
        next_h = rest.find("\n## ", 1)
        block = rest[:next_h] if next_h != -1 else rest
        return "- [ ]" in block or "- [x]" in block or "- [X]" in block


def parse_ticket(path: Path) -> Ticket | None:
    if path.name.startswith("_template"):
        return None
    content = path.read_text(encoding="utf-8")
    id_match = TICKET_ID_PATTERN.search(content)
    status_match = STATUS_PATTERN.search(content)
    tier_match = TIER_PATTERN.search(content)
    if not id_match or not status_match:
        return None
    tier = tier_match.group(1) if tier_match else TIER_T2
    return Ticket(
        ticket_id=id_match.group(1),
        path=path,
        status=status_match.group(1).strip(),
        tier=tier,
        content=content,
    )


def load_tickets(tasks_dir: Path) -> list[Ticket]:
    tickets: list[Ticket] = []
    for path in sorted(tasks_dir.glob("AE-*.md")):
        parsed = parse_ticket(path)
        if parsed is not None:
            tickets.append(parsed)
    return tickets


def can_transition(ticket: Ticket, new_status: str) -> list[str]:
    errors: list[str] = []
    if new_status not in ALL_STATUSES:
        errors.append(f"Invalid status: {new_status}")
        return errors

    if new_status == STATUS_READY and ticket.tier != "T0":
        sections = (
            HOTFIX_MIN_SECTIONS if ticket.tier == TIER_T1 else REQUIRED_READY_SECTIONS
        )
        for section in sections:
            if not ticket.section_has_content(section):
                errors.append(f"Missing or empty section: {section}")
        if not ticket.has_acceptance_criteria():
            errors.append("Missing acceptance criteria checkboxes")

    if new_status == STATUS_IN_DEVELOPMENT:
        min_sections = (
            HOTFIX_MIN_SECTIONS if ticket.tier == TIER_T1 else REQUIRED_READY_SECTIONS
        )
        for section in min_sections:
            if not ticket.section_has_content(section):
                errors.append(f"Missing or empty section: {section}")
        if not ticket.has_acceptance_criteria():
            errors.append("Missing acceptance criteria checkboxes")

    if new_status == STATUS_DEV_COMPLETE:
        if not ticket.section_has_content("## Test Evidence"):
            errors.append("Missing test evidence")
        if not ticket.has_acceptance_criteria():
            errors.append("Acceptance criteria not present")

    if new_status == STATUS_REVIEW:
        dev_report = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
        qa_report = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_QA_SUFFIX}"
        errors.extend(
            _dev_report_errors(dev_report, f"Missing dev summary: {dev_report}")
        )
        if not qa_report.exists():
            errors.append(f"Missing QA report: {qa_report}")

    if new_status == STATUS_DONE:
        if not ticket.section_has_content(SECTION_FINAL_SUMMARY):
            errors.append("Missing final summary")

    return errors


def validate_ticket_file(ticket: Ticket) -> list[str]:
    errors: list[str] = []
    if ticket.status not in ALL_STATUSES:
        errors.append(f"Invalid status: {ticket.status}")

    if ticket.status in (STATUS_READY, STATUS_IN_DEVELOPMENT):
        errors.extend(can_transition(ticket, ticket.status))

    if ticket.status == STATUS_REVIEW:
        errors.extend(can_transition(ticket, STATUS_REVIEW))

    if ticket.status == STATUS_DONE:
        errors.extend(can_transition(ticket, STATUS_DONE))

    if ticket.status == STATUS_DEV_COMPLETE:
        dev_report = REPORTS_DIR / f"{ticket.ticket_id}{REPORT_DEV_SUFFIX}"
        errors.extend(
            _dev_report_errors(
                dev_report,
                f"Status Dev Complete but no dev summary at {dev_report.name}",
            )
        )

    return errors


def _dev_report_errors(report: Path, missing_msg: str) -> list[str]:
    """Validate the dev-summary file backing a Dev Complete / Review transition.

    The file must exist AND not still be the auto-scaffold (AE-0169): existence
    alone never satisfies the gate — the developer must replace the placeholder.
    Returns at most one error message; encapsulated here to keep can_transition /
    validate_ticket_file from branching on each sub-condition.
    """
    if not report.exists():
        return [missing_msg]
    if _is_unfilled_scaffold(report):
        return [f"Dev summary is still an unfilled scaffold: {report.name}"]
    return []


def _is_unfilled_scaffold(report: Path) -> bool:
    """True if the dev-summary still carries the auto-scaffold sentinel (AE-0169)."""
    try:
        return DEV_SUMMARY_SCAFFOLD_MARKER in report.read_text(encoding="utf-8")
    except OSError:
        return False
