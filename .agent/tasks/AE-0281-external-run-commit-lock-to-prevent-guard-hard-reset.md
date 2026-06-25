# AE-0281 — external-run commit lock to prevent guard hard-reset

Status: Intake
Tier: T2
Priority: P2
Type: Quality
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-25
Updated: 2026-06-25

## Goal

Make the AE-0170 external-worktree guard non-destructive: a commit made on the
primary working tree while an external run is live must be BLOCKED up front with
a clear message, not silently `git reset --hard`-ed away after the fact. A
lockfile written by the runner, plus a pre-commit refusal while it exists,
converts a data-loss footgun into a friendly block.

## Problem

(Kaizen failure class C5 — external worktree guard hard-resets local commits.)
`ext_run_guarded` in `scripts/lib/external_agent.sh:143-150` snapshots the
primary HEAD before an external (QA/cold-critic/kaizen) worktree run and, if HEAD
or branch changed during the run, does:

```bash
git -C "$primary" checkout --force "$branch_before"
git -C "$primary" reset --hard "$head_before"
```

There is **no lock** preventing a commit during the run, and the reset is
destructive and silent. In a real session (learnings record 8) a developer
committed on the branch while an external-QA worktree run was in progress; the
guard hard-reset the primary to the pre-run HEAD and discarded the commit — it
was only recovered because it happened to have been pushed
(`git reset --hard origin/<branch>`).

The current behavior is also asymmetric: working-tree changes are reported but
NOT auto-reverted (the safe choice), while committed work IS destroyed — exactly
backwards from a data-safety standpoint.

Source: `.agent/reports/kaizen-session-2026-06-25.plan.md` (proposal P4),
learnings record 8, memory `no-git-add-all-with-uncommitted-work`.

## Scope

- `ext_run_guarded` writes a lockfile (e.g. `.git/EXTERNAL_RUN_ACTIVE` containing
  the pre-run HEAD/branch + a pid/timestamp) at start and removes it on exit
  (including on the FATAL/return-4 paths — use a trap so a killed run still
  cleans up, or make the lock self-expiring/stale-detectable).
- A `.husky/pre-commit` (or a `scripts/ci` helper the hook calls) refuses to
  commit on the primary while the lock exists, printing why + how to proceed
  (wait for the run, or remove a stale lock).
- Reconsider the destructive reset: at minimum, when HEAD changed AND the new
  commits are NOT reachable from the pre-run HEAD, prefer aborting with guidance
  over `reset --hard` (don't silently destroy reachable-only-locally commits).

## Non-Goals

- Redesigning the worktree isolation model — the guard's intent (keep the
  external run from corrupting the primary) stays; this only makes the failure
  mode safe.
- Locking across unrelated repos / global git operations.

## Acceptance Criteria

- [ ] `ext_run_guarded` creates the lock on start and removes it on every exit
      path (success, FATAL, and signal/kill via trap).
- [ ] A commit attempt on the primary while the lock is present is REJECTED by
      the pre-commit hook with an actionable message — proven by a rule-fires
      test (AE-0180): lock present → commit blocked; lock absent → commit allowed.
- [ ] No code path `git reset --hard`-es commits that are unreachable from the
      pre-run HEAD without first surfacing them to the user (abort-with-guidance).
- [ ] Stale-lock handling documented (how to clear if a run died without cleanup).
- [ ] `docs/guides/` (external-review runbook) documents the lock.

## Gherkin Scenarios

```gherkin
Feature: external-run commit lock

  Scenario: commit blocked during a live external run
    Given an external worktree run is active and the lockfile exists
    When the developer attempts git commit on the primary
    Then the pre-commit hook rejects it with guidance to wait or clear a stale lock

  Scenario: commit allowed when no run is active
    Given no external run is active and no lockfile exists
    When the developer commits
    Then the commit proceeds normally

  Scenario: lock is cleaned up after the run ends
    Given an external run that completes or is killed
    When the runner exits
    Then the lockfile is removed (or detectable as stale)
```

## Delta

### ADDED

- lockfile lifecycle in `ext_run_guarded`
- pre-commit lock check + rule-fires test

### MODIFIED

- `scripts/lib/external_agent.sh`
- `.husky/pre-commit` (or a helper it invokes)
- external-review runbook doc

### REMOVED

- (none) — the destructive reset is made conditional/safe, not removed wholesale

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: rule-fires test for the pre-commit lock
- Docs: external-review runbook
- Prompts/LLM: none
- Observability: none
- Deployment: none (developer tooling)

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0219 (same runner file — `external_agent.sh`; coordinate to avoid
  conflicting edits), AE-0170 (the guard this hardens)

## Implementation Plan

1. Add lock create/remove (with `trap` cleanup) to `ext_run_guarded`.
2. Add the pre-commit check + rule-fires test.
3. Make the `reset --hard` path conditional on reachability; abort-with-guidance
   otherwise.
4. Document stale-lock recovery in the runbook.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-25 HH:mm

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
