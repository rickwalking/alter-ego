# AE-0156 — Fix husky/lint-staged pre-commit hook for the frontend/ layout

Status: Intake
Tier: T2
Priority: High
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

The husky pre-commit hook runs `eslint --fix` + `prettier --write` on staged
frontend files successfully **from the repo root**, so contributors no longer
need `--no-verify` and the local format/lint safety net is restored.

## Problem

Source: kaizen `.agent/reports/kaizen-AE-0152-0155.plan.md` (failure class #1).
`.husky/pre-commit` runs `npx lint-staged` from the **repo root**, but the
lint-staged config AND `eslint`/`prettier` live in `frontend/package.json` /
`frontend/node_modules`. So the hook `ENOENT`s on any commit touching frontend
files, and **every commit across AE-0152..0155 and PR #22 used `--no-verify`**,
silently bypassing the format/lint-fix safety net (the wave-QA integrity agent
even observed the hook fire mid-run and leave a staged edit). The gates were
reproduced manually instead, but the local pre-commit net is currently dead.

## Scope

- `.husky/pre-commit` + a root lint-staged config (`.lintstagedrc.json` or root
  `package.json`): route `frontend/**/*.{ts,tsx,json,css,md}` staged files through
  the frontend toolchain (run in `frontend/`, e.g. `cd frontend && eslint --fix` /
  `prettier --write`, or a function-form config). Mirror for backend if it has a
  staged-files formatter.
- Verify it works **from the repo root AND inside a git worktree** (this epic ran
  in a worktree).

## Non-Goals

- Changing the lint/format rules themselves (only fix where/how they run).
- Adding new pre-commit checks beyond restoring eslint/prettier on staged files.

## Acceptance Criteria

- [ ] Committing a deliberately-unformatted staged `.ts`/`.tsx` file from the repo
      root triggers the hook and auto-fixes it (no `--no-verify` needed).
- [ ] The hook no longer `ENOENT`s; it resolves the frontend `eslint`/`prettier`.
- [ ] Works from the repo root and inside a `git worktree`.
- [ ] Contributor docs (or the hook output) make clear `--no-verify` is no longer
      required for routine commits.

## Gherkin Scenarios

```gherkin
Feature: Pre-commit formats staged frontend files

  Scenario: An unformatted staged file is auto-fixed on commit from the repo root
    Given a staged frontend .ts file with formatting issues
    When the user commits from the repo root (no --no-verify)
    Then lint-staged runs the frontend eslint/prettier and the file is fixed
    And the commit succeeds
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
