# AE-0552 — Manual Reprocessar for stuck carousels through the queue

Status: In Development
Tier: T3
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Kimi
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0552-manual-carousel-reprocess
Kanban Card: TBD
Created: 2026-10-25
Updated: 2026-10-25

## Goal

Pedro can manually reprocess a stuck carousel from its workspace or the Fila panel, immediately kicking the generation worker without running any phase in the web process.

## Problem

Dead letters, retry waits, stale running rows, and generating projects with no active generation run have no safe owner-driven recovery through the queue. The Fila panel also hides unstaged work, computes inconsistent positions/ETAs, lacks running liveness and accessible confirmations, polls after 403, and can alarm Pedro for his own cancel.

## Scope

- Owner/admin project reprocess endpoint plus admin run/panel actions, optimistic project CAS and generation-status CAS, idempotent existing-run responses, 409 refusal codes, and audit events.
- Stuck: latest dead_letter; retry_wait; running with non-null heartbeat older than the configured reaper threshold and a free drive lock; a generating project with no queued/running run beyond the dispatcher grace. Not stuck: owner review/approval, normal queued/unstaged work, fresh running, null/unknown heartbeat, or a busy drive lock.
- Manual metadata in existing JSON payloads; no schema change, backlog insert, or autopilot daily-cap consumption. Failed-terminal autopilot replacements carry a manual reason excluded from the existing cap query.
- PgQueuer priority 1 for owner-requested recovery, priority 0 for ordinary work. The active drive is never preempted; FIFO is preserved by job id/creation within each class. This is Pedro's new bounded exception to the original no-priority FIFO rule.
- Separate maintenance entrypoint: dispatch-only after reprocess, full promotion + recovery + dispatcher for Processar fila agora. Scheduled and manual full passes share a non-blocking session advisory lock.
- Workspace and Fila progress, refusal reasons, safe failure codes, PT/EN strings, accessible confirmations, null-position and 403 fixes, unstaged rows and one shared position/ETA implementation.
- Suppress only owner_queue_cancelled Telegram failure notices. Apply #290 findings: safe SQL exception metadata without SQL/parameters, and module-top recovery import if the graph permits it.

## Non-Goals

- Direct in-process generation, new schema/migration/deploy one-shot, feature flags, changing retry budgets, reaping rules, or normal daily-cap semantics.
- Recovering unsupported END/approved-hold/published states, treating null heartbeat as stale, or cancelling a live driver.
- Running the daily recovery scan after every Reprocessar; dispatch-only never promotes backlog or consumes recovery attempts.

## Acceptance Criteria

- [ ] AC1 POST reprocess is owner/admin, CAS-guarded, audited, idempotent on sequential/concurrent double-click, returns the existing run where appropriate, and never directly invokes a graph.
- [ ] AC2 Every required stuck kind re-enqueues the correct current-phase work and kicks the worker: dead_letter, retry_wait, stale running, and generating with no active run.
- [ ] AC3 Waiting-owner, normal queued, fresh-running, null-heartbeat, busy-lock, unsupported, and stale-version requests return 409 with stable reasons and no work/audit duplicate.
- [ ] AC4 Manual work creates no backlog item and is excluded from the autopilot daily cap; priority 1 runs next after the current drive, with FIFO inside each priority class.
- [ ] AC5 Processar fila agora runs the scheduled promotion/recovery/dispatcher functions on demand; manual-vs-scheduled and double-click races cannot double-promote, double-revive, purge twice, or send duplicate summaries.
- [ ] AC6 Workspace and Fila show queued position/ETA → running phase → safe failure reason, with PT/EN strings and an immediate board/workflow refresh.
- [ ] AC7 Retry_wait never renders #0; running rows show started_at and attributed heartbeat age; action aria-labels include the theme; Cancel/Discard require confirmation.
- [ ] AC8 Polling stops after the first 403; unstaged runs appear once with the same position function as Telegram; ETA accounts for running elapsed and retry_wait rejoin time.
- [ ] AC9 owner_queue_cancelled produces no Telegram failure notice while retaining audit/outbox and genuine failure notices.
- [ ] AC10 A SQLAlchemy error carrying SQL and bound parameters yields only exception type plus safe DBAPI class/SQLSTATE in logs and summary, never SQL, parameters, prompt, or payload.
- [ ] AC11 queue_bridge imports mark_recovery_attempt at module top unless a demonstrated cycle requires retaining the local import, in which case the exact cycle is documented in the dev summary.

## Gherkin Scenarios

- `backend/tests/features/carousel_manual_reprocess_ae0552.feature`
- `backend/tests/features/queue_panel_recovery_ae0552.feature`
- `frontend/tests/features/carousel-manual-reprocess.feature`
- `frontend/tests/features/workflow-queue-panel.feature`

## Delta

### ADDED

- Manual recovery command/service, maintenance control entrypoint, shared lock and PgQueuer priority/acceleration.
- Project/panel/workspace actions and progress, shared position/ETA core, synthetic unstaged/orphan rows, safety regressions.

### MODIFIED

- Existing revive, staging, dispatcher, board readers, autopilot cap query, notice-kind selection, queue panel and polling.
- ADR-0026 records Pedro's priority-1 recovery exception and maintenance control job.

### REMOVED

- No direct editor-only recovery limitation, #0 fallback, perpetual 403 polling, duplicate position formulas, raw recovery exception messages, or owner-cancel alarm.

## Affected Areas

- Backend: generation queue, autopilot queue board/cap/notices, carousel workflow API, worker maintenance.
- Frontend: Fila panel, carousel workspace, hooks/schemas/constants/i18n/tests.
- Database: existing rows/JSON and PgQueuer priority only; no schema change.
- API: reprocess GET/POST, run reprocess POST, maintenance POST, queue response metadata, OpenAPI.
- Tests: unit/integration/race/API/RTL, backend and frontend Gherkin.
- Docs: ticket, architecture plan, ADR-0026, reports.
- Prompts/LLM: none.
- Observability: safe audit/action logs and recovery failure metadata.
- Deployment: existing worker only; no new service or migration.

## Dependencies

- Blocks: none.
- Blocked by: AE-0526 (#288 merged). #290/AE-0553 must be in the final base for findings 8-9.
- Related: AE-0522, AE-0523, AE-0524, AE-0548 and ADR-0026.

## Implementation Plan

1. Write Gherkin and failing classifier/service/panel tests for every stuck/refusal/race and nine review findings.
2. Implement shared reprocess service, CAS/store operations, priority/acceleration and maintenance entrypoint/locks.
3. Implement shared position/ETA, unstaged/heartbeat board data, cap/notice safety and recovery follow-ups.
4. Implement workspace/Fila actions, progress, confirmations, polling termination and PT/EN copy.
5. Run targeted suites, full backend/frontend gates and integrity, independent QA, rebase on current main including #290, then push once and monitor CI.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-25

Ticket and architecture plan created after #288 merged. #290 findings 8-9 are required before the final push.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- 2026-10-25 (Pedro): manual recovery uses priority 1 without preempting the active drive; ordinary work stays at 0 and FIFO holds inside each class.
- 2026-10-25 (Pedro): Reprocessar kicks dispatch only; Processar fila agora runs the full promotion/recovery pass. Both stay in the worker and reuse existing functions.
- 2026-10-25 (Pedro): no schema or feature flag. Manual metadata lives in existing payloads; failed-terminal replacements carry a manual reason excluded from the cap.
- 2026-10-25 (Pedro): null/unknown heartbeat is not stale. A stale running takeover requires a free project drive lock and a fresh state check.
- 2026-10-25 (Pedro): ETA remains approximate; running elapsed and retry_wait lower bounds are included, while owner/lock waits cannot be predicted exactly.
- 2026-10-25 (Pedro): skeptical review requires attempt-UUID fencing, explicit picked-job cancellation, full autopilot/project takeover keys, successor identity, cap NOT EXISTS on manual rows, one deduped maintenance path, and shared existing-retry semantics.

## Blockers

#290/AE-0553 is still open at implementation start; rebase onto it before applying findings 8-9 and before the final push.

## Final Summary

Pending.
