# AE-0187 — Frontend: Suspense data-loading migration ratchet (ADR-010 enforcement)

Status: Ready
Tier: T3
Priority: Medium
Type: Refactor
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P4) + skeptical review.
> **Relates to** AE-0146 (Suspense ADR-010, accepted).

## Goal

Close the gap between accepted ADR-010 and the code: stop NEW manual-loading, migrate existing.

## Problem

~39 files use manual `isLoading` vs 1 using `<Suspense>`; ADR-010 unenforced.

## Scope

- Ratchet: block NEW manual-loading data-fetch in changed files; grandfather existing.
- **Prerequisite (skeptical BLOCKER):** define the EXACT AST selector — `isLoading` is overloaded (data-fetch vs local submission vs Query's returned `isLoading` vs types). Allow Query-returned `isLoading`; target only fetch/effect-backed loading.
- Capture an authoritative grandfather baseline (raw grep ~60 ≠ 39); coordinate with AE-0186 (touching grandfathered files).
- Includes `use-blog-post-editor.ts` useEffect state-sync (moved here from AE-0184).

## Non-Goals

- Big-bang rewrite; forcing Suspense where inappropriate.

## Acceptance Criteria

- [ ] A seeded NEW isLoading data-fetch in a changed file is flagged; existing grandfathered.
- [ ] Query-returned `isLoading` is NOT flagged; baseline only shrinks.

## Gherkin Scenarios

```gherkin
Feature: Suspense migration ratchet
  Scenario: New manual loading blocked, Query isLoading allowed
    Given the AST selector
    When a changed file adds a useState-backed fetch loading flag
    Then it is flagged; a useQuery().isLoading is not
```

## Decision Log

- 2026-06-17 — Skeptical review (BLOCKER): selector underspecified, ~60≠39 → added exact-selector prerequisite + authoritative baseline + AE-0186 coordination.

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
