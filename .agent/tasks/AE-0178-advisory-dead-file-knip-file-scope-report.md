# AE-0178 — Advisory dead-file (knip file-scope) report

Status: Intake
Tier: T1
Priority: Low
Type: Task
Area: Frontend/CI
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A non-blocking `frontend / Dead files (advisory)` report (knip file scope) that
surfaces unused files without forcing risky deletions — complementing the
blocking export-scoped dead-code gate (AE-0172).

## Problem

Source: kaizen `.agent/reports/kaizen-AE-0172-0175.plan.md` (failure class #3) +
the AE-0172 QA finding. The AE-0172 blocking gate is **export/type-scoped**
(`--include exports,types,...`); unused **files** are not surfaced anywhere.
Unscoped `knip` reports ~117 "unused files" — mostly barrel-reachable or
app-router/framework files — too noisy to block, but worth visibility (like the
`frontend / Duplication (tests, advisory)` job).

## Scope

- Add a non-blocking `frontend / Dead files (advisory)` step running knip with
  file scope, posting a PR summary (reuse `scripts/ci/post-pr-quality-comment.sh`);
  `continue-on-error: true`. Wire via `gates.sh frontend:dead-files` (advisory).
- Tune `knip.json` so genuine framework entrypoints aren't counted (the Next.js/
  Storybook/Vitest entries already exist).

## Non-Goals

- Do not refactor unrelated code
- Do **not** make dead-file detection blocking (acceptable noise; advisory only).
- Do not delete the reported files in this ticket.

## Acceptance Criteria

- [ ] Advisory job runs knip over file scope and posts a PR summary.
- [ ] Job never fails the PR (`continue-on-error`).
- [ ] Documented as advisory in `docs/guides/qa-checkpoints.md` (next to the
      blocking dead-code gate and the duplication-tests advisory).

## Repro Steps

1. `cd frontend && npx knip --include files` → ~117 unused-file findings, none of
   which the current (export-scoped) blocking gate surfaces.

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
