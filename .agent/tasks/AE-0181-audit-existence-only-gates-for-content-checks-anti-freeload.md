# AE-0181 — Audit existence-only gates for content checks (anti-freeload)

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Audit gates that pass on the mere *existence* of an artifact (a file, a section, a
report) and harden them to check meaningful *content*, so automation or
placeholders can't satisfy them vacuously.

## Problem

Kaizen learning K3 from the Phase 8 Class B QA wave. `schema.py` gated the
Dev Complete / Review transitions on `dev_report.exists()` only; once AE-0169
auto-scaffolded that report, an unfilled placeholder satisfied the gate (finding
M1). Fixed for that one gate (a scaffold-sentinel content check). The same
existence-only smell likely exists elsewhere — e.g. ticket-section presence checks
that accept `Pending`/`TBD`, report-presence checks that don't inspect content,
and (discovered during this cleanup) **two `Review` tickets sharing one report
slot so one freeloads on the other's report** (the AE-0145..0158 ID collisions).

## Scope

- Inventory existence-only gates across `scripts/agent_tasks/schema.py`,
  `scripts/ci/`, and the QA checkpoints.
- For each, decide: add a content/sentinel/non-placeholder check, or document why
  existence is sufficient.
- Specifically: make report-presence checks attribute the report to the right
  ticket (the freeload problem), not just glob by ID.

## Non-Goals

- Not re-litigating the AE-0145..0158 renumbering (tracked separately).
- Not a rewrite of the validation engine; targeted hardening only.

## Acceptance Criteria

- [x] Inventory of existence-only gates produced (in the dev-summary).
- [x] Each hardened with a content check or a documented justification — `qa_report`
      now content+attribution checked (mirrors dev_report); section/dev_report were
      already content-aware (AE-0166/0169), documented as such.
- [x] Report-attribution check prevents one ticket freeloading on another's report
      (`_report_attributed_to`: report body must name the ticket id, for both
      dev-summary and QA report) + non-blocking duplicate-ID warning in validate_all.
- [x] Tests cover a seeded vacuous-pass for each newly-hardened gate
      (empty QA report, unattributed QA report, unattributed dev-summary).

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related:

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 HH:mm

Ticket created.

## Files Touched

- `scripts/agent_tasks/schema.py` — `_qa_report_errors` (content + attribution),
  `_report_attributed_to`, `_has_meaningful_content`; `_dev_report_errors` gains
  attribution; both callers thread the ticket id.
- `scripts/agent_tasks/validate_all_tickets.py` — non-blocking duplicate-ID warning.
- `backend/tests/unit/agent_tasks/test_schema.py` — 4 seeded vacuous-pass / freeload tests.
- `.agent/reports/AE-00{18,19,20,21,22,23,28}.dev-summary.md` — added truthful
  `Ticket: AE-00XX` attribution lines (legacy reports that predated the convention;
  each is the unique owner of its id, so this is a data fix, not loosening).

### Existence-only gate inventory (AC 1)

| Gate | Where | Before | After |
|------|-------|--------|-------|
| Ready/InDev section presence | `schema.section_has_content` | already rejects Pending/TBD/None | unchanged (already content-aware) |
| Dev-summary at Dev Complete/Review | `_dev_report_errors` | existence + scaffold-sentinel (AE-0169) | + **attribution** to the ticket id |
| QA report at Review | `qa_report.exists()` | **existence only** | + **non-trivial content** + **attribution** |
| AC checkboxes | `has_acceptance_criteria` | checks for `- [ ]/[x]` | unchanged (already content-aware) |

## Test Evidence

```bash
$ cd backend && uv run pytest tests/unit/agent_tasks/ -q
15 passed, 1 skipped
# new: empty QA report -> "empty or a placeholder"; QA report naming AE-1234 ->
# "not attributed to AE-9996"; dev-summary naming AE-1234 -> "not attributed to
# AE-9996"; real attributed reports -> pass.

$ uv run python scripts/agent_tasks/validate_all_tickets.py
WARNING: duplicate ticket IDs (report-freeload risk, AE-0181): AE-0145..0148
All 202 ticket(s) OK

$ bash scripts/ci/check-integrity.sh backend  -> 0 blockers
```

### Newly red-boarded / noted tickets

None remained red. Tightening dev_report attribution initially flagged 7 legacy
reports (AE-0018..0023, AE-0028) that genuinely owned their slot but predated the
`Ticket:` convention — fixed by adding the truthful attribution line (not a loosen).
Duplicate IDs **AE-0145/0146/0147/0148** are surfaced as a non-blocking WARNING
(renumbering is out of scope per Non-Goals; per-id attribution still blocks the
generic freeload).

## QA Report

Pending.

## Decision Log

- Did NOT add a *blocking* duplicate-ID failure: renumbering AE-0145..0148 is an
  explicit Non-Goal. Surfaced as a non-blocking warning instead so the board stays
  green while the risk is visible.
- QA reports are not auto-scaffolded (only dev-summaries are), so the QA content
  check is "≥3 non-empty lines" rather than a scaffold sentinel.

## Blockers

None.

## Final Summary

Pending.
