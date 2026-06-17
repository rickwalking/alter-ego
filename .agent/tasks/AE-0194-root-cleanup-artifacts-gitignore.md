# AE-0194 — Root cleanup: remove committed screenshots/snapshots/tmp + fix .gitignore

Status: Ready
Tier: T1
Priority: Low
Type: Task
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
De-bloat the repo root and stop debug artifacts from recurring.

## Problem
Source: kaizen production-readiness sweep. Committed junk: ~7MB screenshots
(carousel-*.png, marinssolutions-carousel.png, slide-1-check.png), 10 Playwright
a11y snapshots (create-page, login-*, langfuse-*), and stale `tmp/docker-compose.prod.yml`.
`.gitignore` lacks patterns for these. KEEP `clickhouse-config/` (live Langfuse mount).

## Scope
- `git rm` the screenshots, the 10 snapshot files, and `tmp/`.
- Extend `.gitignore`: `carousel-*.png`, `*-check.png`, `tmp/`, snapshot patterns.

## Non-Goals
- Removing clickhouse-config/ (actively mounted).

## Acceptance Criteria
- [ ] Listed artifacts removed from git; `.gitignore` prevents recurrence.
- [ ] clickhouse-config/ untouched; compose still references the canonical prod file.

## Gherkin Scenarios
```gherkin
Feature: Clean repo root
  Scenario: new screenshot is ignored
    Given the extended .gitignore
    When a carousel-*.png is created
    Then git does not track it
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
- Tests:
- Docs:
- Deployment:

## Dependencies
- Blocks:
- Blocked by:
- Related:

## Implementation Plan
1. See Scope.

## QA Checklist
- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log
### 2026-06-17 00:00
Emitted by kaizen production-readiness sweep (.agent/reports/kaizen-production-readiness.plan.md).

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
