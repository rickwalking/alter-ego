# AE-0553 — Daily recovery survives one failing item

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Kimi
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0553-recovery-scan-isolation
Kanban Card: TBD
Created: 2026-10-25
Updated: 2026-10-25

## Goal

One failed dead-letter revive neither stops the daily recovery scan nor consumes that item's single recovery attempt.

## Problem

The scan commits the dead letter's `recovery_attempt` marker and then revives the autopilot run in a separate transaction. If the revive raises, later items, stale recovery, purge, counts, and the owner summary are skipped while the failed item cannot be retried the next day.

## Scope

- Make the generation-run recovery marker and autopilot revive atomic in the existing queue bridge transaction.
- Contain and log each item failure without payload, prompt, traceback, or exception-message text in the structured log.
- Continue the remaining scan stages and include failed item ids and bounded reasons in Pedro's summary.
- Preserve exactly-once successful revival under concurrent scans and the Telegram owner retry CAS.
- Unit and database integration coverage, including rollback and concurrency.

## Non-Goals

- Changing recovery eligibility, schedules, retry budgets, queue ordering, or summary counts.
- Changing stale-run recovery, checkpoint pruning, schema, migrations, or deployment.
- Retrying a failed item again within the same scan.

## Acceptance Criteria

- [ ] AC1 Given several dead letters where reviving one raises, When the scan runs, Then the others are still revived, purge and the owner summary still run, and the summary names the failed item with its reason.
- [ ] AC2 Given a revive that raises, Then that dead letter's one try is not used up, so the next day's scan retries it once; a successful revive is never repeated.
- [ ] AC3 Given a concurrent scan or Pedro's "Tentar de novo", Then the dead letter cannot be revived twice.
- [ ] AC4 Each failed item emits one structured log with its generation-run id, autopilot-run id, and exception type, without payload, prompt, traceback, or exception-message text.

## Gherkin Scenarios

`backend/tests/features/daily_recovery_scan_ae0553.feature`.

## Delta

### ADDED

- Per-item failure reports and content-free structured logs.
- Atomic mark-and-revive transaction and race tests.

### MODIFIED

- The queue bridge receives the generation-run id with the autopilot-run id for daily dead-letter recovery.

### REMOVED

- The scan's separate committed mark before revive.

## Affected Areas

- Backend: recovery scan, queue bridge, recovery store, generation-queue facade.
- Frontend: none.
- Database: transaction behavior only; no schema change.
- API: none.
- Tests: recovery unit and integration tests plus Gherkin.
- Docs: ticket and architecture plan.
- Prompts/LLM: none.
- Observability: per-item structured warning and owner summary failures.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: AE-0524, merged in PR #286.
- Related: AE-0523 owner retry and ADR-0026.

## Implementation Plan

1. Add Gherkin and failing tests for isolation, rollback, summary/log contents, and concurrency.
2. Move the daily marker into the bridge's existing revive session through a session-scoped generation-queue facade operation.
3. Add per-item exception containment, failure reports, summary formatting, and structured logging.
4. Run targeted tests, full backend gates and integrity, then QA and CI.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-25

Ticket and transaction design created after PR #286 merged into `origin/main`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-25 (Pedro): use one transaction for marking and reviving rather than a compensating marker update; no schema or feature flag.
- 2026-10-25 (Pedro): logs contain ids and exception type only; the owner summary contains the failed item id and a bounded reason.

## Blockers

None.

## Final Summary

Pending.
