# AE-0225 — Frontend data-loading pattern: React Suspense ADR + guide + QA checklist

Status: In Development
Tier: T2
Priority: Medium
Type: Docs
Area: Docs/Arch
Owner: Agent
Agent Lane: planner → architect → developer → qa → release
Branch: feat/dev-wave-ae0220-0227
Kanban Card: AE-0225
Created: 2026-06-16
Updated: 2026-06-18

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

- [x] ADR written and set to `accepted`, listed in CLAUDE.md ADR index — **ADR-010 `docs/decisions/0010-suspense-data-loading.md` (Status: Accepted), indexed in CLAUDE.md line 131.**
- [x] Guide documents the decision tree with at least one good + one bad example — **`docs/guides/suspense-data-loading-guide.md` has ✅/❌ examples.**
- [x] QA checkpoint reference (`docs/guides/qa-checkpoints.md`) references the pattern — **added "Frontend data-loading pattern (Suspense)" checkpoint under §2.**

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

### 2026-06-18

Renumbered from **AE-0146** to resolve the duplicate-ID collision (AE-0181 dup
warning): AE-0146 is the *Done* same-work twin; this pending (Ready) ticket kept
its own card. Suspense data-loading is **not** complete — components still use the
manual loading pattern (see also the AE-0187 migration ratchet). No content change.

### 2026-06-18 — implemented

This ticket covers only the **documentation** standard (ADR + guide + QA checklist),
NOT the code migration (that is AE-0187, still open). The ADR (`0010-suspense-data-
loading.md`, Accepted) and guide were shipped by the Done twin AE-0146; the genuine
gap was the QA-checkpoint reference (AC3), now added to `qa-checkpoints.md`. Status
held at In Development pending the wave finalization.

## Files Touched

- `docs/guides/qa-checkpoints.md` — new "Frontend data-loading pattern (Suspense)" checkpoint under §2 Code Quality.

## Test Evidence

```
$ grep -n "0010-suspense" CLAUDE.md                       → indexed (line 131)
$ sed -n '/## Status/,/Accepted/p' docs/decisions/0010-suspense-data-loading.md → Accepted
$ grep -nE "✅|❌" docs/guides/suspense-data-loading-guide.md → good/bad examples present
```
Docs-only; no code/gate impact (the migration is tracked separately in AE-0187).

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
