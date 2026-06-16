# AE-0144 — Frontend gate: forbid inline component/hook interfaces (colocated types.ts + baseline ratchet)

Status: Ready
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A blocking frontend gate that forbids declaring `interface`/`type` inline in
component (`.tsx`) and hook files, requiring them in a colocated `types.ts`. The
project convention already exists (`modules/publishing/blog/types.ts`,
`modules/quality/types.ts`, `modules/persona/types.ts`) but is unenforced.

## Problem

Source: kaizen incident on PR #21 (`.agent/reports/kaizen-pr21.plan.md`). A
reviewer left the SAME comment — "move component interface to an external file" —
**13 times** across `modules/publishing/blog/**` and `modules/knowledge/**`
because nothing in the lint gate catches inline type declarations. Examples:
`blog/components/rich-text-editor.tsx:8`, `blog/components/ai-suggestion-panel.tsx:16`,
`blog/hooks/use-accessibility-check.ts:7`, `blog/hooks/use-blog-posts.ts:18`.
Human review should not be the enforcement mechanism for a documented convention.

## Scope

- New regex+file-walk scanner `frontend/scripts/check-component-types.mjs`,
  modeled on the existing `frontend/scripts/feature-boundary-scan.mjs`.
- `component-types-baseline.json` ratchet: grandfather the ~13 existing
  violations; the baseline count may only ever DECREASE (matches the
  feature-boundary + integrity ratchet pattern).
- Wire into `npm run lint` chain + add a `frontend:component-types` gate to
  `scripts/ci/gates.sh` so CI and `/qa-agent` both run it (single source of truth).
- Document the rule in `frontend/AGENTS.md` and a row in `docs/guides/qa-checkpoints.md`.

## Non-Goals

- Mass-refactoring the 13 existing inline interfaces (baseline grandfathers them;
  they are paid down opportunistically when files are touched).
- Backend type-location rules.

## Acceptance Criteria

- [ ] `check-component-types.mjs` flags an exported/non-trivial `interface`/`type`
      declared in a `.tsx`/hook file that is not a `types.ts`.
- [ ] Baseline grandfathers existing violations; CI is green on the current tree.
- [ ] **The gate FAILS on a seeded NEW inline interface** (prove enforcement works).
- [ ] Baseline count can only decrease (raising it fails review / integrity scan).
- [ ] Gate runs via `bash scripts/ci/gates.sh frontend:component-types` and in the
      frontend lint CI job.
- [ ] Rule documented in `frontend/AGENTS.md` + `docs/guides/qa-checkpoints.md`.

## Gherkin Scenarios

```gherkin
Feature: Component type-location gate

  Scenario: New inline interface in a component is rejected
    Given a colocated types.ts convention and a committed baseline
    When a developer adds "export interface FooProps { ... }" inside foo.tsx
    Then "scripts/ci/gates.sh frontend:component-types" fails
    And the message points to the colocated types.ts it should live in

  Scenario: Pre-existing inline interface in the baseline does not block
    Given an inline interface already recorded in component-types-baseline.json
    When the gate runs on the unchanged file
    Then the gate passes (grandfathered)

  Scenario: Baseline may not be widened
    Given a committed baseline of N violations
    When a change raises the baseline above N
    Then the change is rejected (ratchet up only)
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
