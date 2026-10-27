# AE-0560 — Correct the recovery race event oracle

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Kimi
Branch: fix/ae-0560-recovery-race-deploy
Created: 2026-10-26
Updated: 2026-10-26

## Goal

Make the owner-retry/scan race test validate exactly-once recovery and the committed events for either legitimate winner in both SQLite and PostgreSQL.

## Problem

Deploy run `40416254513`, including its rerun, fails deterministically on main `8add9696c83d443959d8204e7804842e21782b39`: escalated recovery expects `(1, 1)` audit/outbox rows but gets `(2, 2)`, and failed-terminal recovery expects `(0, 0)` but gets `(1, 1)`. Backend Quality Gates passes the same SHA because it supplies PostgreSQL, while Deploy runs the same complete pytest suite without `DATABASE_URL` and therefore uses SQLite. The race test permits either path to win but its event totals assume a scan win. An owner win correctly adds `carousel.reprocess.requested` to the normal recovery events.

## Scope

- Reproduce the deploy-only failure and run the race 20 times against a local Docker PostgreSQL database.
- Establish from committed run, generation, audit, and outbox state whether recovery happens twice or the test oracle ignores a valid owner event.
- Assert event identity pairs and event-type multiplicity for the actual winner without changing the once-only recovery assertion.
- Keep the production recovery and audit behavior unchanged unless runtime evidence proves a defect.

## Non-Goals

- No workflow environment change to hide the SQLite failure.
- No removed or relaxed once-only, generation-count, replacement-count, audit, or outbox assertion.
- No schema, API, feature flag, unrelated recovery refactor, or local mutation run.

## Acceptance Criteria

- [x] AC1 The two deploy assertions reproduce locally without `DATABASE_URL`, and 20 pre-fix PostgreSQL repetitions provide evidence for the workflow-dependent result.
- [x] AC2 Given either recovery winner, exactly one path reports success and the existing queued-run and replacement invariants remain unchanged for escalated and failed-terminal runs.
- [x] AC3 Audit and outbox contain matching event id/type pairs: one autopilot state-change event for an escalated revive, none for a failed-terminal replacement, and one manual-reprocess event exactly when the owner retry wins.
- [ ] AC4 The corrected race suite passes on SQLite and repeatedly on PostgreSQL, followed by targeted backend checks and CI green on every PR workflow.

## Gherkin Scenarios

- `backend/tests/features/daily_recovery_scan_ae0553.feature`: `Concurrent recovery and owner retry revive only once`.

## Repro Steps

1. Without `DATABASE_URL`, run `uv run pytest tests/integration/test_daily_recovery_races_ae0553.py::test_forced_owner_retry_and_scan_revive_only_once -q` from `backend`.
2. With a local Docker PostgreSQL `DATABASE_URL`, run the same node 20 times through `~/bin/laptop-gate heavy`.
3. Compare committed event types with the winner derived from the owner response and the unchanged exactly-once assertion.

## Affected Areas

- Backend: no production change indicated by the reproduction.
- Frontend: none.
- Database: disposable local PostgreSQL only; no migration.
- API: none.
- Tests: recovery race integration test and its Gherkin scenario.
- Docs: this ticket and required delivery reports.
- Deployment: unblocks the existing Deploy test job; no workflow edit.

## Dependencies

- Blocks: production deployment of #294 and merge readiness on main.
- Blocked by: none.
- Related: AE-0553, AE-0559, ADR-0026.

## Implementation Plan

1. Capture the deterministic SQLite failure and 20-run PostgreSQL baseline.
2. Update the Gherkin event contract, then replace broad scan-only totals with stronger winner-aware event identity/type assertions.
3. Verify both database dialects, run non-mutation backend verification and independent QA, then open and watch the PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-26

Ticket created on `fix/ae-0560-recovery-race-deploy` at current `origin/main` (`8add9696c83d443959d8204e7804842e21782b39`). Static tracing found one successful revive in both reported failures; the additional rows are the intentional owner manual-reprocess audit/outbox pair.

The SQLite deploy path reproduced both failures exactly. Twenty pre-fix PostgreSQL runs passed. The test now checks matching audit/outbox event id/type pairs and exact event-type counts for the observed winner; the original exactly-once and business-state assertions are unchanged. Four SQLite race tests, 20 post-fix PostgreSQL repetitions, and 19 related PostgreSQL recovery/retry tests pass.

## Files Touched

- `backend/tests/features/daily_recovery_scan_ae0553.feature`
- `backend/tests/integration/test_daily_recovery_races_ae0553.py`
- `.agent/tasks/AE-0560-recovery-race-event-oracle.md`
- `.agent/reports/AE-0560.dev-summary.md`
- `.agent/reports/AE-0560.qa.md`

## Test Evidence

- Deploy attempts 1 and 2 fail with the same two assertions; Backend Quality Gates passes on the same SHA.
- Deploy invokes the full pytest suite with coverage but no PostgreSQL service or `DATABASE_URL`; Backend Quality Gates invokes the same suite through `backend:test` with PostgreSQL 16 and `DATABASE_URL`. Neither uses xdist, markers, nor test selection to exclude this test.
- Pre-fix SQLite: two failed with the exact deploy counts `(2, 2) != (1, 1)` and `(1, 1) != (0, 0)`. The preceding exactly-once and run/replacement assertions passed.
- Pre-fix PostgreSQL 16 Docker: 20 consecutive runs of the two parametrized owner/scan cases passed, 40 cases total, through `~/bin/laptop-gate heavy`.
- Post-fix SQLite: four race tests passed; Ruff format and lint checks passed.
- Post-fix PostgreSQL: another 20 consecutive runs passed, 40 cases total; 19 related race, atomicity, scan, and Telegram retry tests passed.

## QA Report

Pending.

## Decision Log

- 2026-10-26 (Pedro): preserve the once-only assertion and fix the demonstrated root cause rather than hiding the deploy failure.

## Blockers

None.

## Final Summary

Pending.
