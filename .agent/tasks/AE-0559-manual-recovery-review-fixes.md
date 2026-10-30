# AE-0559 — Fix forward manual recovery review findings

Status: Done
Tier: T2
Priority: High
Type: Bug
Area: Cross-cutting
Owner: Kimi
Agent Lane: planner → architect → developer → qa → release
Branch: fix/ae-0559-manual-recovery-review-fixes
Kanban Card: TBD
Created: 2026-10-26
Updated: 2026-10-26

## Goal

Close the A1/B1/C1 blockers and required review nits from #291 without changing its owner-facing contracts, especially the incorrect scheduled maintenance behavior and autopilot daily-cap accounting.

## Problem

#291 merged at `4748f4df` before its final review fixes landed. In-place manual recovery can remove an already-counted autopilot run from the daily cap, both cron schedules enqueue a full maintenance pass, queued scheduled work can repeat a full pass, and confirmation focus is lost. Telegram retry also needs one root transaction for its callback claim, recovery, audit, and outbox.

## Scope

- Count only failed-terminal replacements as cap-exempt manual runs; preserve the original run's cap consumption for in-place dead-letter and retry-wait recovery.
- Scope existing-manual-run SQL reads, return `can_reprocess=False` with progress for an existing run, and audit Telegram retries with the configured application owner.
- Use promote/scan/full maintenance modes, per-mode dedupe, one-job concurrency, and full-pass supersession of queued scheduled work without cancelling dispatch jobs.
- Keep Telegram recovery in a savepoint, defer worker notification until root commit, and relay outbox events only at the root transaction outcome.
- Add confirmation focus/open/Escape/restore behavior, per-row pending sets, safe Fila refusal text, run-scoped polling, and idle workspace hiding without losing accepted progress.
- Preserve safe logging, dynamic clock seeding compatible with AE-0558, and original-job-id FIFO documentation.

## Non-Goals

- No schema changes, feature flags, direct in-process generation, changed retry budgets, or normal daily-cap semantics.
- No fixed historical timestamps, unsafe picked-job cancellation, or changes to AE-0558's current-time seed behavior.

## Acceptance Criteria

- [x] AC1 Failed-terminal replacements remain outside the cap, while in-place dead-letter and retry-wait recovery leave its count unchanged.
- [x] AC2 08:05 promotes only, 04:00 scans only, and Processar fila agora runs full maintenance. A full pass subsumes queued scheduled work without duplicate summaries or dispatch loss.
- [x] AC3 Telegram callback dedupe, recovery, audit, and outbox share one root transaction; rollback permits retry and notification occurs only after commit.
- [x] AC4 Existing-run lookup is SQL-scoped and returns `can_reprocess=False` with run identity and progress.
- [x] AC5 Cancel and Discard move focus into confirmation, close on Escape, and restore focus on Back/Escape; Discard has explicit keyboard coverage.
- [x] AC6 Ordinary active work polls slowly, accepted recovery polls by run id, idle controls hide, accepted progress remains visible, known 409 reasons survive, and pending rows are independent.
- [x] AC7 Maintenance/API failures are logged safely, dynamic clock tests remain date-independent, and accelerated jobs retain original-job FIFO.

## Gherkin Scenarios

- `backend/tests/features/carousel_manual_reprocess_ae0552.feature`
- `backend/tests/features/telegram_queue_flow_ae0523.feature`
- `backend/tests/features/daily_recovery_scan_ae0524.feature`
- `backend/tests/features/workflow_event_ordering.feature`
- `frontend/tests/features/carousel-manual-reprocess.feature`

## Delta

### ADDED

- Maintenance mode coordination, supersession regression coverage, root-transaction outbox tests, and accepted-run progress lifecycle coverage.

### MODIFIED

- Cap predicate, Telegram recovery composition, existing-run lookup, maintenance schedules/gateways, queue-row actions, polling, and workspace visibility.

### REMOVED

- Broad manual-run cap exclusion, full-pass behavior from both cron schedules, test-only recovery helper, and single-row pending state.

## Affected Areas

- Backend: autopilot cap/Telegram recovery, generation maintenance, outbox transaction hooks, worker schedules, API logging.
- Frontend: Fila actions/hooks and carousel workspace recovery controls.
- Database: existing JSON payloads and PgQueuer jobs only; no migration.
- API: existing responses and route descriptions only; no new endpoint.
- Tests: backend unit/Postgres integration and frontend RTL/hook suites with Gherkin updates.
- Docs: ADR-0026, OpenAPI description, this ticket and reports.
- Prompts/LLM: none.
- Observability: structured maintenance and deferred-dispatch failures; root-only outbox relay.
- Deployment: existing worker; no new service or one-shot.

## Dependencies

- Blocks: production correctness for the next scheduled maintenance passes.
- Blocked by: none.
- Related: AE-0552/#291, AE-0558/#293, AE-0553, ADR-0026.

## Implementation Plan

1. Preserve cap accounting and make Telegram recovery root-transactional.
2. Split maintenance modes and suppress sequential as well as concurrent duplicate work.
3. Complete accessibility, polling, visibility, and Fila concurrency fixes.
4. Verify targeted Postgres/RTL suites, lint, typecheck, full captures, integrity, and independent QA.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-26

Review blockers and nits implemented on the original branch, transplanted cleanly onto current origin/main after #291 and #293 merged. Cross-mode sequential duplication found by independent QA was fixed before the fix-forward branch was prepared.

## Files Touched

- Autopilot cap, owner actions, queue control and existing-run recovery files.
- Maintenance domain/application/gateway/worker files and recovery logging.
- Outbox hooks, backend/frontend features and regression suites, ADR-0026 and OpenAPI.
- Fila and workspace controls, hooks, types, tests, and the editorial facade.
- `.agent/reports/AE-0559.dev-summary.md` and `.agent/reports/AE-0559.qa.md`.

## Test Evidence

- Current base: 65 targeted backend tests and 86 targeted frontend tests passed, including Postgres cap, transaction, maintenance, and Discard keyboard cases.
- Current base: backend:lint/type and frontend:lint/typecheck PASS; Ruff and Prettier checks clean.
- Full candidate capture before transplant: backend 7743 passed, 2 pre-existing skips, 26 non-mutation gates PASS; frontend 378 files/3029 tests, 18 non-mutation gates PASS.
- Independent Codex confirmation: QA_VERDICT PASS after the cross-mode and Discard fixes.
- Integrity: zero blockers and zero warnings; removed assertions are stronger contract checks as documented in the dev summary.

## QA Report

`.agent/reports/AE-0559.qa.md`.

## Decision Log

- 2026-10-26 (Pedro): only failed-terminal replacements are cap-exempt; in-place recovery never frees a cap slot.
- 2026-10-26 (Pedro): scheduled maintenance remains promote-only or scan-only; on-demand full maintenance subsumes queued scheduled modes while preserving dispatch.
- 2026-10-26 (Pedro): AE-0558's current-time seed behavior remains; the bridge test injects the same seeded clock rather than restoring a historical timestamp.
- 2026-10-26 (Pedro): accelerated queued jobs retain original job ids and original-creation FIFO rather than being re-enqueued only to reorder them.

## Blockers

None. Backend and frontend mutation jobs remain CI-only checks on the PR head.

## Final Summary

AE-0559 fixes the merged #291 review blockers without changing its API shape. Cap accounting, schedule boundaries, sequential maintenance dedupe, Telegram atomicity, accessible confirmation, and recovery progress are covered by targeted tests, full non-mutation captures, and independent QA.
