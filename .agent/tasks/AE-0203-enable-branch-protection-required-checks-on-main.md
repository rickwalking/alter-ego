# AE-0203 — Enable branch protection on main (require quality-gate checks)

Status: Ready
Tier: T1
Priority: High
Type: Task
Area: DevOps/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

`main` cannot be merged with red or pending required CI. The quality gates become
*blocking at merge*, not advisory.

## Problem

Source: kaizen production-readiness re-check (2026-06-17). The repo has **no branch
protection on `main`** (`allow_auto_merge: false`); `gh pr merge --auto` falls back
to an **immediate** squash-merge. PR #31 merged while its backend mutation/test CI
was still pending. Every gate built (gates.sh, integrity, mutation, etc.) is
undermined if PRs can merge red. This is the single biggest production-readiness
gap remaining after the docker/lint/docs sweeps.


## CRITICAL implementation finding (2026-06-17)

All three gate workflows are **path-filtered** (`backend-quality-gates` on
`backend/**`, `frontend-quality-gates` on `frontend/**`, `agent-ticket-hygiene`
on `.agent/**`). GitHub blocks a PR on any REQUIRED check that does not run, so
naively requiring the gate checks would **permanently deadlock** path-scoped PRs
(a frontend-only PR would wait forever on backend checks). There is NO single
existing check that runs on every PR.

**Therefore the required-checks part needs an always-running aggregator**, not a
plain settings change:
- Add `.github/workflows/ci-gate.yml` triggered on ALL `pull_request`s (no path
  filter) with one `ci-gate` job that resolves green when the relevant
  path-filtered gates passed OR were correctly skipped (e.g. via the
  changed-paths + wait-for-checks / `re-actors/alls-green` pattern, treating
  skipped-by-path as pass).
- Require ONLY `ci-gate` as the protected check.
- Validate: frontend-only, backend-only, and docs-only PRs all reach a green
  `ci-gate` without hanging; a real gate failure makes `ci-gate` red.

## Phasing / Status

- **Phase 1 (DONE 2026-06-17):** safe protection applied via `gh api` — block
  force-pushes + deletions on `main`, require conversation resolution, no required
  status checks (so nothing deadlocks). Verified live.
- **Phase 2 (this ticket's remaining work):** the `ci-gate` aggregator above, then
  add it as the single required status check (the actual "no merging red CI" goal).

## Scope

- Enable GitHub branch protection on `main` (Settings → Branches, or `gh api`):
  - **Require status checks to pass before merging** + **require branches up to date**.
  - Required checks = the BLOCKING gates only:
    - backend: `Lint & Format`, `Strict Diff (args & complexity)`, `Type Check`,
      `Architecture`, `Docstrings`, `Security`, `Test & Coverage`,
      `Migrations (fresh DB)`, `Mutation (blocking ≥75%)`, `Dead Code`,
      `Integrity (anti-gaming)`
    - frontend: `Lint`, `Lint (changed)`, `Type Check`, `Build`, `Duplication`,
      `Dead code`, `Legacy guard`, `Legacy inventory`, `Test`,
      `E2E auth baseline`, `Security`, `Format`, `Schema drift`,
      `Integrity (anti-gaming)`
    - `agent / validate tickets`
  - **Exclude advisories** (must NOT be required): `frontend / Mutation (advisory)`,
    `frontend / Duplication (tests, advisory)`.
  - Require ≥1 PR review; block force-pushes + deletions.
- Apply via gh (admin token), e.g.:
  ```bash
  gh api -X PUT repos/rickwalking/alter-ego/branches/main/protection \
    -H "Accept: application/vnd.github+json" \
    -f 'required_status_checks[strict]=true' \
    -F 'required_status_checks[contexts][]=backend / Test & Coverage' \
    -F 'required_status_checks[contexts][]=frontend / Lint' \
    ...  # full context list above
    -F 'enforce_admins=false' \
    -F 'required_pull_request_reviews[required_approving_review_count]=1' \
    -F 'restrictions=' 2>/dev/null
  ```

## Non-Goals

- Requiring the advisory checks (would block on non-blocking signal).
- Enabling repo-level auto-merge (optional; separate decision).

## Acceptance Criteria

- [ ] Branch protection active on `main`; `gh api repos/.../branches/main/protection`
      returns the required-checks list.
- [ ] **A PR with a failing required check CANNOT be merged** (verify with a seeded
      red PR — the merge button/`gh pr merge` is blocked).
- [ ] Advisory checks (Mutation advisory, Duplication tests advisory) do NOT block.
- [ ] `gh pr merge --auto` now genuinely waits for green (no immediate-merge fallback).

## Gherkin Scenarios

```gherkin
Feature: main requires green CI to merge
  Scenario: red required check blocks merge
    Given branch protection requires the quality-gate checks
    When a PR has a failing "frontend / Lint" check
    Then the PR cannot be merged until it is fixed

  Scenario: advisory checks do not block
    Given Mutation (advisory) is failing but all required checks pass
    When the PR is merged
    Then the merge succeeds
```

## Delta

### ADDED
- GitHub branch-protection rule on `main` (repo setting; not a tracked file).
### MODIFIED
- (none — repo configuration)
### REMOVED
- (none)

## Affected Areas

- Backend:
- Frontend:
- Tests:
- Deployment: GitHub branch protection / merge policy

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0142 (exit gate), gates.sh single-source-of-truth

## Implementation Plan

1. Apply branch protection per Scope (needs repo admin).
2. Seed a red PR to confirm it blocks; confirm advisories don't.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 00:00

Emitted by kaizen production-readiness re-check (main-no-branch-protection finding).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

Needs repo admin to apply the GitHub setting.

## Final Summary

Pending.
