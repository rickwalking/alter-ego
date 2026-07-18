# AE-0320 — background resume self-deadlock main session row lock vs heartbeat session blocks run and reaper

Status: Ready
Tier: T2
Priority: High
Type: Bugfix
Area: backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-18
Updated: 2026-07-18

## Goal

Describe the outcome this ticket should produce.

## Problem

Describe the problem or opportunity.

## Scope

- Resume runner: never hold an open transaction across LLM/network awaits -
  commit before long-running engine work; use short-lived sessions per write
  batch (align with the AE-0107 write-owner seam).
- Heartbeat writer: must not contend with the run's own main transaction -
  write through the same session/tx, or guarantee the main tx is closed during
  generation; add `lock_timeout` so a heartbeat can fail fast + log instead of
  queueing silently forever.
- Reaper: flip stale runs with `lock_timeout`/`SKIP LOCKED` + terminate/alert
  path so it can never be blocked by the run it is reaping.
- Postgres-backed integration regression: slow (stubbed) LLM + concurrent
  heartbeat + reaper tick; assert no lock pileup and gate reached.
- Observability: alert when `idle in transaction` on app sessions exceeds N
  minutes (pg_stat_activity scrape or statement_timeout/idle_in_transaction_
  session_timeout evaluation for app roles).

## Non-Goals

- ...

## Acceptance Criteria

- [ ] Heartbeat writes carry a transaction-scoped lock_timeout on Postgres and skip it on SQLite.
- [ ] Stage-boundary beats are single-attempt, never raise, and log on failure; the resume flow continues.
- [ ] A blocked reaper flip fails fast (no wedged worker tick), logs carousel_run_reap_blocked, and retries next tick.
- [ ] The drift reconciler converges a failed row whose checkpoint is parked awaiting_human at a DIFFERENT phase (row phase/status updated, lock_version + run_epoch bumped, run columns cleared, logged).
- [ ] Same-phase failures and mid-step checkpoints are never converged.
- [ ] The raw-update allowlist gate covers the new reconciler write site (allowlist + survey test in lockstep).

## Gherkin Scenarios

See `tests/features/carousel_run_lock_safety.feature` (scenarios authored first, tests reference them).

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

### 2026-07-18 HH:mm

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
