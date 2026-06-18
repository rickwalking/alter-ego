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
    STATUS_INTAKE,
    STATUS_READY,
    STATUS_REVIEW,
)

TICKET_ID_PATTERN = re.compile(r"^# (AE-\d{4}) —", re.MULTILINE)
STATUS_PATTERN = re.compile(r"^Status:\s*(.+)$", re.MULTILINE)
TIER_PATTERN = re.compile(r"^Tier:\s*(T[0-3])$", re.MULTILINE)

# A QA report with fewer than this many non-empty lines is treated as an
# empty/placeholder file rather than a real report (AE-0181 content check).
_MIN_REPORT_CONTENT_LINES = 3


def _invalid_status_message(value: str) -> str:
    """Self-documenting error for an unknown ticket status (AE-0222).

    Lists every valid status and names the entry state so an author who guesses
    a wrong value (e.g. ``Todo``) sees the fix without reading ``constants.py``.
    """
    valid = ", ".join(ALL_STATUSES)
    return (
        f"Invalid status: {value}. Valid statuses: {valid}. "
        f"New tickets enter at '{STATUS_INTAKE}' ('{STATUS_READY}' is T0-only)."
    )


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
        errors.append(_invalid_status_message(new_status))
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
            _dev_report_errors(
                dev_report, ticket.ticket_id, f"Missing dev summary: {dev_report}"
            )
        )
        errors.extend(
            _qa_report_errors(
                qa_report, ticket.ticket_id, f"Missing QA report: {qa_report}"
            )
        )

    if new_status == STATUS_DONE:
        if not ticket.section_has_content(SECTION_FINAL_SUMMARY):
            errors.append("Missing final summary")

    return errors


def validate_ticket_file(ticket: Ticket) -> list[str]:
    errors: list[str] = []
    if ticket.status not in ALL_STATUSES:
        errors.append(_invalid_status_message(ticket.status))

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
                ticket.ticket_id,
                f"Status Dev Complete but no dev summary at {dev_report.name}",
            )
        )

    return errors


def _dev_report_errors(report: Path, ticket_id: str, missing_msg: str) -> list[str]:
    """Validate the dev-summary file backing a Dev Complete / Review transition.

    The file must exist, NOT still be the auto-scaffold (AE-0169), AND be
    attributed to THIS ticket (AE-0181) — existence alone never satisfies the
    gate, and a report written for a different ticket of the same ID must not be
    freeloaded. Returns at most one error; encapsulated here to keep
    can_transition / validate_ticket_file from branching on each sub-condition.
    """
    if not report.exists():
        return [missing_msg]
    if _is_unfilled_scaffold(report):
        return [f"Dev summary is still an unfilled scaffold: {report.name}"]
    if not _report_attributed_to(report, ticket_id):
        return [
            f"Dev summary {report.name} is not attributed to {ticket_id} "
            f"(its body never names the ticket — possible report freeload, AE-0181)."
        ]
    return []


def _qa_report_errors(report: Path, ticket_id: str, missing_msg: str) -> list[str]:
    """Validate the QA report backing a Review transition (AE-0181).

    Previously gated on existence alone, which let a Review ticket freeload on a
    QA report written for a *different* ticket sharing the same AE-#### id (the
    AE-0145..0148 collisions). Now the report must exist, carry non-trivial
    content (not an empty/placeholder file), AND name this ticket in its body.
    """
    if not report.exists():
        return [missing_msg]
    if not _has_meaningful_content(report):
        return [f"QA report is empty or a placeholder: {report.name}"]
    if not _report_attributed_to(report, ticket_id):
        return [
            f"QA report {report.name} is not attributed to {ticket_id} "
            f"(its body never names the ticket — possible report freeload, AE-0181)."
        ]
    return []


def _report_attributed_to(report: Path, ticket_id: str) -> bool:
    """True if the report body names `ticket_id`, binding it to exactly this ticket.

    Stops a Review/Dev-Complete ticket from satisfying its report gate with a
    report authored for another ticket that happens to share the AE-#### id.
    """
    try:
        return ticket_id in report.read_text(encoding="utf-8")
    except OSError:
        return False


def _has_meaningful_content(report: Path) -> bool:
    """True if the report carries more than an empty/whitespace-only placeholder."""
    try:
        text = report.read_text(encoding="utf-8")
    except OSError:
        return False
    non_empty = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return len(non_empty) >= _MIN_REPORT_CONTENT_LINES


def _is_unfilled_scaffold(report: Path) -> bool:
    """True if the dev-summary still carries the auto-scaffold sentinel (AE-0169)."""
    try:
        return DEV_SUMMARY_SCAFFOLD_MARKER in report.read_text(encoding="utf-8")
    except OSError:
        return False
