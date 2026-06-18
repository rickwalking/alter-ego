# AE-0146 — Frontend data-loading pattern: React Suspense ADR + guide + QA checklist

Status: Ready
Tier: T2
Priority: Medium
Type: Docs
Area: Docs/Arch
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A documented, agreed standard for frontend data-loading/loading states (React
`<Suspense>` vs manual `isLoading`), so reviewers and QA apply it consistently
instead of flagging it ad hoc.

## Problem

Source: kaizen incident on PR #21 (`.agent/reports/kaizen-pr21.plan.md`). The
reviewer asked for React Suspense twice (`blog/components/accessibility-checker.tsx:67`,
`distribution/components/regenerate-strategy-section.tsx:58`). Today Suspense is
used once in the whole frontend; manual `useState` loading is the norm. There is
no documented pattern, so it cannot be enforced fairly. A brittle lint rule would
produce noise — this is better captured as an ADR + guide + QA checklist item.

## Scope

- `docs/decisions/00NN-frontend-data-loading-suspense.md` (MADR 4.x): when to use
  Suspense + lazy vs manual state; relationship to TanStack Query.
- `docs/guides/frontend-loading-patterns.md`: concrete examples (good/bad).
- Add a "loading-state pattern" item to the QA code-quality checklist.

## Non-Goals

- A hard lint gate for Suspense (unreliable to lint; out of scope).
- Migrating existing components (separate refactor tickets if desired).

## Acceptance Criteria

- [ ] ADR written and set to `accepted`, listed in CLAUDE.md ADR index.
- [ ] Guide documents the decision tree with at least one good + one bad example.
- [ ] QA checkpoint reference (`docs/guides/qa-checkpoints.md`) references the pattern.

## Gherkin Scenarios

```gherkin
Feature: Documented data-loading standard

  Scenario: Reviewer has a canonical reference
    Given the Suspense ADR and loading-patterns guide exist
    When a component introduces a manual loading state where Suspense fits
    Then QA cites the guide as the standard rather than an ad-hoc opinion
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

### 2026-06-16 HH:mm

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
