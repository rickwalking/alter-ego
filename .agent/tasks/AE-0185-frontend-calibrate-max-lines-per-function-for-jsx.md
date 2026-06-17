# AE-0185 — Frontend: calibrate max-lines-per-function for JSX (ratchet-down, not exempt)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P3a) + skeptical review.
> **Relates to** AE-0166 (eslint hardening) — note: this CALIBRATES (keeps a ceiling), it does not exempt.

## Goal

Stop `max-lines-per-function` false-flagging legitimate JSX bodies WITHOUT removing the ceiling.

## Problem

The `src/app/**/page.tsx` override caps at 40, firing ~118x because JSX bodies are legitimately longer. (Genuine giants handled by AE-0186, not by relaxing the rule.)

## Scope

- Raise the component threshold to a defensible value (~150, skipBlankLines+skipComments) for page/component `.tsx`; keep 30/40 for lib/hooks logic.
- Add the threshold to `scripts/ci/check-integrity.sh` `HIGHER_IS_GAMING` (frontend-scoped) so it can only ratchet DOWN; verify the diff parser handles `{ max: N }` config-object form.

## Non-Goals

- Setting the rule `off` for `.tsx` or bumping it to silence a giant (loosening — kaizen invariant).

## Acceptance Criteria

- [ ] Reasonable components pass; rule still FAILS on a seeded over-threshold component.
- [ ] Threshold registered in check-integrity (raise = flagged); pure-logic limits unchanged.
- [ ] Count components 40–threshold; pick the lowest defensible value.

## Gherkin Scenarios

```gherkin
Feature: Calibrated component size rule
  Scenario: Bloated component still fails
    Given the calibrated threshold
    When a component exceeds it
    Then the lint gate fails (ceiling preserved)
```

## Decision Log

- 2026-06-17 — Skeptical review (WARN): check-integrity key doesn't exist yet → added subtask + diff-parser verification; 150 may be loose → count-and-pick-lowest.

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

Implemented + QA PASS (2026-06-17, dev→QA loop, branch kaizen/frontend-debt-capture):
eslint errors 0, depcheck unused 0, no raw fetch in hooks (seeded rule fires on fetch / allows refetch),
max-lines-per-function 116→42, tsc clean, 884 tests pass, zero suppressions.

## Final Summary

Pending.
