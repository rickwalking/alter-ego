# AE-0181 — Audit existence-only gates for content checks (anti-freeload)

Status: Intake
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

- [ ] Inventory of existence-only gates produced (in the dev-summary).
- [ ] Each hardened with a content check or a documented justification.
- [ ] Report-attribution check prevents one ticket freeloading on another's report.
- [ ] Tests cover a seeded vacuous-pass for each newly-hardened gate.

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

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
