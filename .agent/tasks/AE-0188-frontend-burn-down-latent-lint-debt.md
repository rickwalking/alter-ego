# AE-0188 — Frontend: burn down latent lint debt (async-correctness first)

Status: Ready
Tier: T2
Priority: High
Type: Bugfix
Area: Frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

> **Captured from** `.agent/reports/kaizen-frontend-debt.plan.md` (P5) + skeptical review.
> **Relates to** AE-0166 (harden warnings→errors). **Async Phase 1 already shipped in PR #28.**

## Goal

Burn down latent eslint debt; LOCK IN enforcement (it is unenforced today).

## Problem

Skeptical review (BLOCKER, verified at eslint-changed.mjs:33): `lint:changed` uses `--quiet`, so warn-level rules have ZERO CI enforcement — this is ratchet UP, not HOLD. Remaining: no-unnecessary-condition ~68, prefer-nullish ~49, complexity ~37. (Async-correctness 32 → 0 done in PR #28.)

## Scope

- Phase 2: drive down no-unnecessary-condition / prefer-nullish-coalescing / complexity. Fix root cause; never disable a rule.
- Phase 3 (the actual ratchet): promote these rules to enforced on changed files (`--max-warnings=0` or a `lint:changed:strict` gate).

## Non-Goals

- Disabling/downgrading any rule (loosening); the component giants (AE-0186).

## Acceptance Criteria

- [ ] Target rule counts → 0 (or justified per-line); no rule disabled.
- [ ] Enforcement locked in: the cleaned rules FAIL on a seeded violation in a changed file.

## Gherkin Scenarios

```gherkin
Feature: Lint-debt burn-down + lock-in
  Scenario: Cleaned rule now blocks new violations
    Given --quiet replaced by enforced rules on changed files
    When a changed file introduces a cleaned-rule violation
    Then the lint-changed gate fails
```

## Decision Log

- 2026-06-17 — Skeptical review (BLOCKER, verified): "warn→ERROR on changed files" was false (--quiet); reclassified UP + added Phase 3 lock-in.

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

Captured from kaizen frontend-debt analysis (renumbered; AE-0172..0182 owned by PR #29).

### 2026-06-17 (execution)

; Ph3 lock-in pending a rule reaching 0.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Final Summary

Pending.
