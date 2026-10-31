# AE-0582 — Deploy workflow drops its test job (tests stay in PR CI)

Status: Done
Tier: T1
Priority: High
Type: Chore
Area: CI/CD
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0582-deploy-without-test-job
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

A merge to main goes straight to the deploy job. Pedro's decision (2026-10-31): tests run in CI, not in CD.

## Problem

`deploy.yml` re-ran the backend pytest and frontend vitest suites (~15 min, AE-0417 timeout 40) before every
deploy (`needs: test`), although PR CI (`ci-gate`) already runs the full gate set on the same code. Pedro turns on
"Require branches to be up to date before merging" for main, so a PR's ci-gate tests exactly what lands.

## Scope

- Remove the `test` job and the deploy job's `needs: test` from `.github/workflows/deploy.yml`. Nothing else in the
  file changes: deploy steps, the `prod-deploy` concurrency, `if: github.ref == 'refs/heads/main'` and
  `workflow_dispatch` stay.

No public or user-visible behavior change. CI/config ticket: unit tests pin the workflow shape (seeded check: the
job test fails on the old `deploy.yml`). Affected gates: none changed; `ci-gate.yml` and the quality-gate workflows
are untouched.

## Non-Goals

- Branch protection (Pedro flips strict mode himself).
- `ci-gate.yml` or the backend/frontend quality-gate workflows.

## Acceptance Criteria

- [x] AC1 `deploy.yml` has only the `deploy` job, with no `needs`.
- [x] AC2 The main-only `if`, the `prod-deploy` concurrency (no cancel) and `workflow_dispatch` are unchanged.
- [x] AC3 The first deploy after merge goes straight to the deploy job and finishes green.

## Gherkin Scenarios

- `backend/tests/features/deploy_without_test_job_ae0582.feature`

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [x] Tests
- [x] Deploy workflow

## Dependencies

None.

## Progress Log

### 2026-10-31 15:00

Test job and `needs: test` removed; workflow-shape test added (fails on the old `deploy.yml`, 1 failed / 1 passed).

## Files Touched

- `.github/workflows/deploy.yml`
- `backend/tests/features/deploy_without_test_job_ae0582.feature`
- `backend/tests/unit/scripts_ci/test_deploy_without_test_job_ae0582.py`

## Test Evidence

Full local backend gates on main at 29b45139 (contains this change): pass 26, fail 0, skip 1 (mutation, CI only).
An earlier branch run had one known aiosqlite setup error (AE-0583); its `backend:test` rerun passed (7902 passed). GATES_JSON in
`.agent/reports/AE-0582.dev-summary.md`. The shape test fails on the old `deploy.yml` (1 failed, 1 passed).

## QA Report

Independent review of the scope by the coordinating session: only the test job and `needs: test` removed.

## Blockers

None.

## Final Summary

Merged to `main` in PR #318 (0734d7da, 2026-10-31): the deploy workflow no longer re-runs the test suites. The first
deploy after it ran only the deploy job and finished green in about 8 minutes.
