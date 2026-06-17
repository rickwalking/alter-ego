# AE-0196 — Docs cleanup: delete 11 superseded/noise docs + mark phase plans Done

Status: Ready
Tier: T1
Priority: Low
Type: Docs
Area: Docs
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal
Remove stale/noise docs and stamp completed phase plans.

## Problem
Source: kaizen production-readiness sweep (docs audit, 99 files; 26 orphaned).
A DELETE bucket of 11 superseded/one-off docs and 6 shipped phase plans lacking a Status.

## Scope
- DELETE: plan-sse-migration.md (v1), cloudflare-ws-debug.md, neon-shell-redesign-verification.md,
  plans/neon-migration-qa-todo.md, plans/f2231ece-carousel-lower-third-correction.md,
  tasks/fix-public-chat-401-production.md, backend/BACKEND_SUMMARY.md,
  backend/BACKEND_COMPLETE_GUIDE.md, frontend/IMPLEMENTATION_PLAN.md,
  frontend/carousel-creator-plan.md (+ verify each is unreferenced before delete).
- Add `Status: Done` to docs/plans/phase-1..6 plans.

## Non-Goals
- The deprecate/index work (AE-0197).

## Acceptance Criteria
- [ ] 11 docs deleted; no remaining inbound links to them (grep).
- [ ] phase-1..6 plans carry `Status: Done`.

## Gherkin Scenarios
```gherkin
Feature: Docs hygiene
  Scenario: superseded doc removed
    Given plan-sse-migration.md is replaced by v2
    When the audit runs
    Then the v1 draft no longer exists and nothing links to it
```

## Delta
### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas
- Frontend:
- Docs:
- Tests:

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

### 2026-06-17 (executed, dev→QA loop, PR #31)
DONE — 9 docs deleted; phase-1..6 Status: Done [commit 18b329d]. QA: integrity 0 blockers, eslint 0 errors, 884 FE tests pass.

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
