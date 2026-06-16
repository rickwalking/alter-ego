# AE-0149 — Frontend gate: jscpd source-scoped duplication detector (ratchet-down threshold)

Status: Dev Complete
Tier: T2
Priority: High
Type: Task
Area: Frontend/CI
Owner: developer-skill
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0149-0151-frontend-duplication-gate
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A blocking, source-scoped copy-paste detection gate (jscpd) for the frontend,
wired into the single-source-of-truth runner, with a threshold that may only
ratchet DOWN.

## Problem

Source: kaizen analysis (`.agent/reports/kaizen-jscpd.plan.md`). Measured
`npx jscpd frontend/src`: **1.94% source duplication (39 clones, 542 lines)** —
uncaught by any gate (no copy-paste detector in the lint chain or CI). NOTE: the
all-files figure is 7.22%, but ~73% of that is test boilerplate; the blocking
gate must therefore be SOURCE-scoped (tests excluded) to avoid noise and harmful
test-DRYing. Ref: https://jscpd.dev/getting-started/agent-skill

## Scope

- Add `jscpd` devDependency + `frontend/.jscpd.json`:
  `format: [typescript, tsx]`, `minTokens: 50`, `minLines: 5`, `threshold: 2`
  (≈ current source level), `reporters: [console, json]`,
  `ignore: ["**/node_modules/**","**/dist/**","**/*.test.*","**/*.spec.*","**/*.stories.*"]`.
- `npm run lint:dup` → chain into `npm run lint` (next to `lint:boundaries`).
- Add `frontend:duplication` gate to `scripts/ci/gates.sh`; add a
  `frontend / Duplication` job to `.github/workflows/frontend-quality-gates.yml`.
- Add jscpd `threshold` to `scripts/ci/check-integrity.sh` (raising it = loosening).
- Document in `frontend/AGENTS.md` + `docs/guides/qa-checkpoints.md`.

## Non-Goals

- Including test files in the BLOCKING gate (advisory only — see AE-0151).
- Refactoring existing clones (separate ticket AE-0150).

## Acceptance Criteria

- [x] `bash scripts/ci/gates.sh frontend:duplication` passes at the current source level (1.45% < threshold 2).
- [x] **The gate FAILS on a seeded duplicate source block** (proven by `src/scripts/duplication-gate.test.ts`).
- [x] Test/spec/story files are excluded from the blocking gate (`.jscpd.json` ignore globs; test-asserted).
- [x] `threshold` can only decrease (raising it flagged by `check-integrity.sh`: `.jscpd` added to CONFIG_HINT, `"threshold"` added to HIGHER_IS_GAMING).
- [x] Gate runs in CI (`frontend / Duplication` job) and via the lint chain (`npm run lint` → `lint:dup`); documented in AGENTS.md + qa-checkpoints.

## Gherkin Scenarios

```gherkin
Feature: Frontend duplication gate

  Scenario: New source duplication above threshold is rejected
    Given jscpd threshold is set at the current source level
    When a change pushes source duplication above the threshold
    Then "scripts/ci/gates.sh frontend:duplication" fails

  Scenario: Test boilerplate does not trip the blocking gate
    Given test/spec/story globs are ignored
    When duplicated setup exists only in *.test.ts files
    Then the blocking gate passes

  Scenario: Threshold may not be raised
    Given a committed jscpd threshold of T
    When a change raises the threshold above T
    Then check-integrity flags it as gate-loosening (ratchet up only)
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
