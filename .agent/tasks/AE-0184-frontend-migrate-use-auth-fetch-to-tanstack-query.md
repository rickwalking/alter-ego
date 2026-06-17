# AE-0184 — Frontend: migrate use-auth fetch->TanStack Query + forbid fetch in hooks

Status: Ready
Tier: T2
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P2) + skeptical review.
> **Relates to** AE-0166 (TanStack-Query-over-fetch lint rule).

## Goal

No raw `fetch` in data hooks; lock it in with a refetch-safe lint rule.

## Problem

Only **1** hook uses raw fetch — `modules/identity/hooks/use-auth.ts` (lines 13,36). (Skeptical review: the original "2 hooks" was a `fetch(`↔`refetch(` grep false positive; `use-blog-post-editor.ts` already uses Query — its useEffect state-sync belongs with AE-0187.)

## Scope

- Migrate `use-auth.ts` to TanStack Query OR document an auth-flow exception.
- Add eslint `no-restricted-syntax` forbidding `fetch(` under `src/**/hooks/**`.

## Non-Goals

- `use-blog-post-editor.ts` (already on Query — see AE-0187).

## Acceptance Criteria

- [ ] `use-auth.ts` on Query (or exception documented); no raw `fetch(` under hooks.
- [ ] Rule FAILS on a seeded `fetch(` in a hook and does NOT flag `refetch(`.

## Gherkin Scenarios

```gherkin
Feature: Hooks use TanStack Query
  Scenario: A new fetch in a hook is rejected, refetch is allowed
    Given the no-fetch-in-hooks rule
    When a hook calls fetch() directly
    Then the lint gate fails; refetch() is unaffected
```

## Decision Log

- 2026-06-17 — Skeptical review (WARN, verified at use-blog-post-editor.ts:33,63): scoped to use-auth; refetch-safe selector.

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
