# AE-0177 — Standardize diff-base resolution across diff-scoped gates

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A shared diff-base/changed-files resolver used by every diff-scoped gate, so a
missing merge base (stacked branch / diverged `origin/main`) never silently
degrades a gate to a no-op.

## Problem

Source: kaizen `.agent/reports/kaizen-AE-0172-0175.plan.md` (failure class #2).
Diff-scoped gates hand-roll `git diff BASE...HEAD` (merge-base form). On a stacked
branch or when `origin/main` has diverged, that fails with `fatal: no merge base`
and the gate silently degrades. AE-0172's `check-dead-code.mjs` hit exactly this
and got a two-ref fallback (`BASE...HEAD` → `BASE HEAD` → advisory), but
`scripts/ci/eslint-changed.mjs` (`lint:changed`) and `scripts/ci/check-integrity.sh`
do NOT have that fallback — so they can silently no-op on the same branch shapes.

## Scope

- Extract a shared `resolve-diff-base` / `changed-files` helper implementing the
  proven pattern: try merge-base `BASE...HEAD`; fall back to two-ref `BASE HEAD`;
  then advisory (with a warning) if neither resolves.
- Use it in `scripts/ci/check-integrity.sh`, `scripts/ci/eslint-changed.mjs`, and
  `frontend/scripts/check-dead-code.mjs` (replace its inline copy).
- Unit-test the resolver (merge-base present / absent / both refs missing).

## Non-Goals

- Do not refactor unrelated code
- Do not change what each gate checks — only how it resolves the changed set.

## Acceptance Criteria

- [ ] A shared resolver exists and is used by check-integrity, lint:changed, and
      the dead-code gate (no per-gate inline copies).
- [ ] On a stacked branch with **no merge base**, the changed set still resolves
      (two-ref fallback) — covered by a unit test.
- [ ] When neither form resolves, gates degrade to advisory **with a visible
      warning** (never a silent pass).

## Repro Steps

1. On a branch stacked off another feature branch whose base has diverged from
   `origin/main`, run `node scripts/ci/eslint-changed.mjs` → it fails to compute
   the changed set / no-ops, rather than falling back like the dead-code gate.

## Progress Log

### 2026-06-17 — partial inline fix (CI unblock)

The backend `diff-cover` case was hardened inline to unblock a stacked PR whose
base (pre-Phase-8 main) lost its merge-base after origin/main advanced:
`gate_backend_diff_cover` now deepens/unshallows the fetch and SKIPs (inconclusive)
rather than crashing. The remaining scope (a shared resolver used by lint:changed
+ check-integrity, with a unit test) is still open.


## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-16 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
