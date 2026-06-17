# AE-0186 — Frontend: refactor oversized page components (HomePageContent, CalendarPage, BlogPostsPage)

Status: Ready
Tier: T3
Priority: High
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P3b) + skeptical review.
> **Relates to / may dedup against** AE-0155 (route-page thinning) + AE-0154 (component rehoming).

## Goal

Split the genuinely oversized components under the AE-0185 calibrated threshold.

## Problem

eslint giants: `HomePageContent` 1133, `CalendarPage` 338, `BlogPostsPage` 229 — maintainability smells (calibration is not a license to keep them).

## Scope

- Extract subcomponents/hooks (presentational vs data/logic) per module conventions + ADR-010.
- One sub-task per component (epic).

## Non-Goals

- Behavior/visual change; relaxing the size rule to avoid the work.

## Acceptance Criteria

- [ ] The three components pass `max-lines-per-function` at the calibrated threshold.
- [ ] Behavior-based tests pass WITHOUT modification (snapshot-only churn doesn't count).
- [ ] Extracted logic units have >=90% branch coverage; e2e green.

## Gherkin Scenarios

```gherkin
Feature: Oversized components refactored
  Scenario: CalendarPage split passes the size gate
    Given CalendarPage was 338 lines
    When sections are extracted
    Then it passes the gate and behavior is unchanged
```

## Decision Log

- 2026-06-17 — Skeptical review (INFO): "zero behavioral change + tests unchanged" is gameable → AC reframed to behavior-tests-pass + >=90% branch coverage on extracted units.

## Delta

### ADDED
- ...
### MODIFIED
- ...
### REMOVED
- ...

## Affected Areas

- Frontend:
- Tests:
- Docs:

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

Captured from kaizen frontend-debt analysis (renumbered to free IDs; AE-0172..0182 owned by PR #29).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Final Summary

Pending.
