# AE-0151 — Frontend: advisory jscpd test-duplication report (non-blocking)

Status: Ready
Tier: T1
Priority: Low
Type: Task
Area: Frontend/CI
Owner: Unassigned
Branch: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

A non-blocking PR report of test-file duplication (jscpd), surfacing the signal
without forcing harmful test-DRYing.

## Problem

Source: kaizen analysis (`.agent/reports/kaizen-jscpd.plan.md`). All-files jscpd
shows 7.22% duplication, ~73% of it test boilerplate (e.g.
`use-editorial-workflow.test.ts` = 1257 dup lines). This is excluded from the
blocking gate (AE-0149) by design, but egregious test duplication is still worth
visibility — as advisory only, like `frontend / Mutation (advisory)`.

## Scope

- Add a non-blocking `frontend / Duplication (tests, advisory)` step that runs
  jscpd over `*.test.*`/`*.spec.*` and posts a PR summary (reuse
  `scripts/ci/post-pr-quality-comment.sh`).
- `continue-on-error: true` — never blocks merge.

## Non-Goals

- Do not refactor unrelated code
- Do NOT make test duplication blocking (acceptable boilerplate).

## Acceptance Criteria

- [ ] Advisory job runs jscpd over test files and posts a PR summary.
- [ ] Job never fails the PR (continue-on-error).
- [ ] Documented as advisory in `docs/guides/qa-checkpoints.md`.

## Repro Steps

1. `cd frontend && npx jscpd src --reporters console` → 7.22% all-files, mostly tests.

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
