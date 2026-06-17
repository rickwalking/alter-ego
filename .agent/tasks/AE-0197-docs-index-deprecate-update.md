# AE-0197 — Docs: add index + deprecate superseded + update 2 stale-but-useful

Status: Ready
Tier: T2
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
Kill the orphan-doc signal and mark history as superseded.

## Problem
Source: kaizen production-readiness sweep. 26 docs have 0 inbound references; ~21 are
historical (completed plans) and 2 are stale-but-useful.

## Scope
- Add `docs/README.md` index linking the KEEP/evergreen docs (progressive disclosure).
- Mark ~21 superseded docs `Status: Superseded` (or move to `docs/archive/`).
- UPDATE 2: SECURITY_IMPLEMENTATION_PLAN.md → security reference; agentic-delivery-system-implementation-plan.md → demote from Proposed.

## Non-Goals
- Deleting the deprecated docs (kept for record).

## Acceptance Criteria
- [ ] docs/README.md index exists; evergreen docs no longer read as orphans.
- [ ] 21 docs marked Superseded; 2 updated to current reality.

## Gherkin Scenarios
```gherkin
Feature: Discoverable docs
  Scenario: index removes orphan signal
    Given docs/README.md links the evergreen docs
    When the orphan audit runs
    Then those docs have an inbound reference
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
