"""Constants for agent ticket tooling."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / ".agent"
TASKS_DIR = AGENT_DIR / "tasks"
REPORTS_DIR = AGENT_DIR / "reports"
BOARD_PATH = AGENT_DIR / "BOARD.md"
CONFIG_PATH = AGENT_DIR / "config.yaml"

TICKET_PREFIX = "AE"
TEMPLATE_FULL = "_template.md"
TEMPLATE_HOTFIX = "_template.hotfix.md"

STATUS_INTAKE = "Intake"
STATUS_SHAPING = "Shaping"
STATUS_READY = "Ready"
STATUS_PLANNING = "Planning"
STATUS_IN_DEVELOPMENT = "In Development"
STATUS_DEV_COMPLETE = "Dev Complete"
STATUS_QA_RUNNING = "QA Running"
STATUS_NEEDS_FIXES = "Needs Fixes"
STATUS_BLOCKED = "Blocked"
STATUS_REVIEW = "Review"
STATUS_READY_TO_MERGE = "Ready to Merge"
STATUS_DONE = "Done"
STATUS_CANCELLED = "Cancelled"

ALL_STATUSES = (
    STATUS_INTAKE,
    STATUS_SHAPING,
    STATUS_READY,
    STATUS_PLANNING,
    STATUS_IN_DEVELOPMENT,
    STATUS_DEV_COMPLETE,
    STATUS_QA_RUNNING,
    STATUS_NEEDS_FIXES,
    STATUS_BLOCKED,
    STATUS_REVIEW,
    STATUS_READY_TO_MERGE,
    STATUS_DONE,
    STATUS_CANCELLED,
)

BOARD_COLUMNS = ALL_STATUSES

TIER_T0 = "T0"
TIER_T1 = "T1"
TIER_T2 = "T2"
TIER_T3 = "T3"

FIELD_STATUS = "Status"
FIELD_TIER = "Tier"

SECTION_ACCEPTANCE_CRITERIA = "## Acceptance Criteria"
SECTION_GOAL = "## Goal"
SECTION_PROBLEM = "## Problem"
SECTION_SCOPE = "## Scope"
SECTION_NON_GOALS = "## Non-Goals"
SECTION_QA_REPORT = "## QA Report"
SECTION_FINAL_SUMMARY = "## Final Summary"
SECTION_TEST_EVIDENCE = "## Test Evidence"

REQUIRED_READY_SECTIONS = (
    SECTION_GOAL,
    SECTION_PROBLEM,
    SECTION_SCOPE,
    SECTION_NON_GOALS,
    SECTION_ACCEPTANCE_CRITERIA,
)

HOTFIX_MIN_SECTIONS = (
    SECTION_GOAL,
    SECTION_PROBLEM,
    SECTION_SCOPE,
    SECTION_NON_GOALS,
    SECTION_ACCEPTANCE_CRITERIA,
)

REPORT_DEV_SUFFIX = ".dev-summary.md"
REPORT_QA_SUFFIX = ".qa.md"

# Sentinel embedded in the auto-scaffolded dev-summary (move_ticket.py, AE-0169).
# Its presence means the report is still an unfilled placeholder, so the
# Dev Complete / Review gates reject it (AE-0166 QA fix — existence alone is not
# enough; the developer must replace the scaffold).
DEV_SUMMARY_SCAFFOLD_MARKER = "> SCAFFOLD"

# --- Machine-readable gate proof (AE-0258) -----------------------------------
# `scripts/ci/gates.sh` (print_summary) emits a line like:
#   GATES_JSON: {"pass":N,"fail":N,"skip":N,"results":[...]}
# The Dev Complete (dev-summary) and Review (qa) transitions require this proof
# so a ticket cannot advance on a prose "all green" or an unverified self-report.
# The proof is self-pasted (hence forgeable) — its authority is CI re-running the
# gates on the same commit, where a forged PASS surfaces as red. This is an
# observability + friction ratchet, NOT a forgery-proof control.
GATES_JSON_MARKER = "GATES_JSON:"

# A per-ticket .qa.md MAY carry the proof by referencing a wave report whose name
# matches this prefix (e.g. `wave-2a.qa.md`); the validator follows the reference.
WAVE_REPORT_PREFIX = "wave-"

# Lenient FIELD-regexes (Critic P1.3): extract fail/skip by field on the RAW line
# rather than re-parsing the whole JSON object, so a future gates.sh change that
# adds or reorders keys does not silently break the parser. They match the field
# anywhere on a GATES_JSON line.
GATES_FAIL_FIELD_RE = re.compile(r'"fail":\s*(\d+)')
GATES_SKIP_FIELD_RE = re.compile(r'"skip":\s*(\d+)')

# --- Dirty-tree taint (AE-0322) ----------------------------------------------
# gate-capture.sh stamps `"dirty":N` into the echoed GATES_JSON line when it ran
# over a working tree with N uncommitted/untracked in-scope source files
# (GATE_CAPTURE_ALLOW_DIRTY=1). Diff-based gates cannot see uncommitted work, so
# a dirty>0 proof BLOCKS the transition unless the dev-summary carries a
# DIRTY_WAIVER: line naming the files and why they belong to other sessions.
GATES_DIRTY_FIELD_RE = re.compile(r'"dirty":\s*(\d+)')
# [^\S\n]* = horizontal whitespace only: the justification must be on the SAME
# line — a bare `DIRTY_WAIVER:` (no files/reason) does not count as a waiver.
DIRTY_WAIVER_RE = re.compile(r"^DIRTY_WAIVER:[^\S\n]*\S", re.MULTILINE)

# The reviewed commit SHA the proof is pinned to (AC: SHA mismatch ⇒ WARNING).
# A report SHOULD record the commit it was produced against on a line like:
#   Commit: <40-or-7-hex>
GATES_COMMIT_FIELD_RE = re.compile(r"^Commit:\s*([0-9a-fA-F]{7,40})\b", re.MULTILINE)

# --- Declared QA mode (AE-0260) ----------------------------------------------
# The .qa.md evidence block must declare the QA mode on a line like `mode: external`.
# External QA is the default/required mode for agent/same-session-authored work;
# `self-fallback` (with a stated reason) is the allowed escape when the external
# toolchain is down. The validator can only check the field is present + allowed —
# it CANNOT detect "same session" (no session identity exists in any markdown).
QA_MODE_FIELD_RE = re.compile(r"^mode:\s*([A-Za-z-]+)", re.MULTILINE | re.IGNORECASE)
QA_MODE_EXTERNAL = "external"
QA_MODE_SELF = "self"
QA_MODE_SELF_FALLBACK = "self-fallback"
ALLOWED_QA_MODES = (QA_MODE_EXTERNAL, QA_MODE_SELF, QA_MODE_SELF_FALLBACK)
