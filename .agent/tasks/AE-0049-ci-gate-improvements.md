# AE-0049 — CI Gate Improvements

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: CI/DevOps
Owner: Unassigned
Agent Lane: developer → qa
Branch: feat/ae-0049-ci-gate-improvements
Kanban Card: AE-0049
Created: 2026-06-10
Updated: 2026-06-10

## Goal

Harden CI gates: elevate mutation testing from advisory to blocking (blocking after 80%+ baseline), add `ruff check --diff` for PR-only detection, and make `diff-cover` a blocking gate for diff coverage.

## Problem

PR #11 had 7 CI gate failures — all advisory. None blocked the PR. Mutation testing ran in advisory mode. The `Strict Diff` gate (max-args, complexity, branches) was advisory. This allowed violations to accumulate.

## Scope

### Mutation Testing (Backend + Frontend)
- Set mutmut baseline score (currently 80.2%)
- Elevate from advisory to **blocking** with threshold >= 75% (below ADR-005's business logic "Low" threshold as starting point)
- Weekly scheduled run on GitHub Actions (per ADR-005 Phase 4)
- If score drops below threshold, CI fails with instructions

### Ruff `--diff` Check
- Add CI step: `ruff check --diff $(git diff --name-only origin/main...)`
- Only checks changed files — fast feedback on PRs
- Fails if new violations introduced

### diff-cover as Blocker
- `diff-cover` currently configured but not blocking
- Elevate to blocking with `fail_under=75`
- Reports on changed lines only, not entire codebase

### Strict Diff Gate
- Make the existing `Strict Diff` check blocking
- Define clear thresholds: max-args=3, max-complexity=10, max-branches=8, max-returns=5, max-locals=12, max-nested-blocks=4

## Non-Goals

- Adding new lint rules beyond those already configured
- Reconfiguring the CI pipeline structure
- Touching deployment CI/CD

## Acceptance Criteria

- [ ] Mutation testing blocks PR if score < 75%
- [ ] Weekly scheduled mutation test runs on GitHub Actions
- [ ] `ruff check --diff` runs on PRs and fails if new violations in changed files
- [ ] `diff-cover` fails PR if diff coverage < 75%
- [ ] Strict Diff gate fails PR if thresholds exceeded
- [ ] All CI gates documented in `docs/guides/qa-checkpoints.md`
- [ ] `cd backend && uv run pytest` passes (integration unaffected)

## Gherkin Scenarios

```gherkin
Feature: CI Gates

  Scenario: new file exceeds max-args
    Given a PR with a function having 5 parameters
    When CI runs the Strict Diff gate
    Then CI fails with "max-args exceeded"

  Scenario: mutation score drops below 75%
    Given a PR that reduces mutation score to 70%
    When CI runs mutation testing
    Then CI fails with score below threshold

  Scenario: PR with excellent coverage
    Given a PR with 85% diff coverage
    When CI runs diff-cover
    Then CI passes

  Scenario: ruff violation in new code only
    Given a PR that introduces a new ruff violation
    When CI runs ruff --diff
    Then CI fails only if the violation is in changed lines
```

## Delta

### MODIFIED

- `.github/workflows/ci.yml` or equivalent CI config
- `docs/guides/qa-checkpoints.md`

### ADDED

- CI workflow steps for ruff --diff, diff-cover blocker, mutation blocker
- Weekly mutation test workflow

## Affected Areas

- Backend: None (CI only)
- Frontend: None (CI only)
- CI: Workflow changes
- Docs: qa-checkpoints.md update

## Dependencies

- Blocks: None
- Blocked by: AE-0048 (no point hardening CI while blanket ignores exist)
- Related: ADR-005

## Implementation Plan

1. Identify CI config location (GitHub Actions workflow file)
2. Add `ruff check --diff $(git diff --name-only origin/main...)` step
3. Add `diff-cover` as blocking step (already configured, just flip fail_under)
4. Configure mutation testing threshold: `--fail-under 75`
5. Add weekly scheduled mutation test workflow
6. Update `docs/guides/qa-checkpoints.md` with new gate descriptions
7. Run `cd backend && uv run pytest` to verify no CI config breakage

## QA Checklist

- [ ] Security reviewed — CI only, no code changes
- [ ] Acceptance criteria validated
- [ ] Edge cases tested — empty diff, first commit on branch, fork PRs
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-10

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

Blocked by: AE-0048

## Final Summary

Pending.
