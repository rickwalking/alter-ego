# AE-0329 — drive strict-index baseline to zero and fold nouncheckedindexedaccess into tsconfig

Status: Intake
Tier: T2
Priority: Medium
Type: Quality
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

`noUncheckedIndexedAccess: true` lives in `frontend/tsconfig.json` itself; the
AE-0324 baseline gate and `tsconfig.strict-index.json` are deleted because
there is nothing left to baseline.

## Problem

AE-0324 measured 76 legacy `noUncheckedIndexedAccess` errors across 30 files
(> the 40-error threshold), so it shipped the >40 branch: a whole-tree scoped
gate (`npm run lint:strict-index`) with a down-only per-file baseline
(`frontend/scripts/strict-index-baseline.json`). New/clean files are already
zero-enforced; the 76 baselined legacy errors remain latent AE-0295-class
crash sites (unguarded `Record[key]`/array access) until fixed. This ticket is
the full-adoption follow-up AE-0324's AC mandated at completion (cold-critic
WARN-4: a spike must not become indefinite deferral).

## Scope

- Fix the baselined errors (guard with `?.` + fallback, `in`/`has` narrowing,
  or explicit undefined handling — NO `!` non-null assertions), ratcheting the
  baseline down with `npm run strict-index:baseline` in reviewable batches
  (suggested: by module, test files last).
- When count reaches 0: set `noUncheckedIndexedAccess: true` in
  `frontend/tsconfig.json`, delete `tsconfig.strict-index.json`,
  `scripts/check-strict-index.mjs`, `scripts/generate-strict-index-baseline.mjs`,
  `scripts/strict-index-baseline.json`, remove `lint:strict-index` from the
  lint chain, and update `AGENTS.md` §1a + the strict-index tests (the
  rule-fires guarantee moves to `npm run typecheck` itself).

## Non-Goals

- No behavioural changes beyond the guards the flag demands.
- No batch may RAISE the baseline (the generator refuses; do not bypass it).

## Acceptance Criteria

- [ ] `scripts/strict-index-baseline.json` count reaches 0 across reviewable
      batches, each with green gates.
- [ ] `noUncheckedIndexedAccess: true` in `frontend/tsconfig.json`;
      `npm run typecheck` fails on a seeded unguarded `Record[key]` access
      (AE-0180 proof migrates from the gate test to typecheck).
- [ ] The AE-0324 gate apparatus is fully removed (no orphan scripts/config)
      and `AGENTS.md` §1a updated to point at the tsconfig flag.
- [ ] No `!` non-null assertion introduced on indexed access to satisfy the
      flag (reviewer/QA check on the diff).

## Repro Steps

1. `cd frontend && npm run lint:strict-index` → today: OK at baseline 76.
2. Any of the 30 baselined files can still crash at runtime on a missing key
   (the AE-0295 shape) — the flag only guards files outside the baseline.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

## Dependencies

Blocked-by: AE-0324 (ships the gate + baseline this ticket drives to zero).

## Progress Log

### 2026-07-22

Ticket created by AE-0324's completion AC (kaizen session-2026-07-22, P4 —
cold-critic WARN-4 forcing function).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
