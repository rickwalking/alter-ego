# AE-0556 — Generation log inside the carousel page

Status: Dev Complete
Tier: T3
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Kimi
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0556-generation-log
Kanban Card: TBD
Created: 2026-10-26
Updated: 2026-10-27

## Goal

The carousel workspace shows a durable, live-updating generation timeline without requiring Langfuse: queue runs, phase attempts and durations, image jobs, export, retries, recovery and final outcomes, with safe diagnostic detail.

## Problem

`generation_runs` retains only current queue state and attempt counters. Existing audit/outbox rows and structured logs have no reliable generation-run correlation, no phase-attempt durations, and may contain feedback, prompts, raw errors or other content that cannot be exposed or copied into a generation log.

## Scope

- Add an append-only `carousel_generation_events` store keyed to a generation run and carousel, recorded at existing queue, phase, image, recovery and export seams.
- Record each event immediately in its own short, best-effort transaction with a 100 ms timeout; never buffer events across steps or runs and never propagate store failures into generation. A timeout drops that event and emits at most one safe warning per 60 seconds in each worker.
- Allowlist flat diagnostic details. Cap serialized details at 4096 bytes, item counts and string lengths, and bound every fixed field. Do not persist exception messages, SQL, bound parameters, prompts, model input/output, personal data, tokens, feedback or image bytes.
- Reuse the safe AE-0553 logging pattern through a shared failure-metadata helper that emits only the exception type and a classified code. Planted secrets and `DBAPIError` SQL/parameters must not reach an event.
- Store a real Langfuse trace id and SDK-generated trace URL when a phase trace exists; Langfuse remains optional.
- Add owner/admin `GET /api/carousels/{project_id}/generation-log`, keyset-paginated newest first with a default of 50 and a maximum of 200 events per page.
- Add a compact PT/EN workspace timeline grouped by run and phase, older runs collapsed, text outcome labels, right-aligned durations, keyboard-native disclosures, load-more and trace links.
- Invalidate the log from the existing workflow SSE/poll state updates; add no new polling connection or interval.
- Purge events older than 30 days in the existing daily recovery purge and cascade event cleanup with their parent run/carousel.
- Ship Alembic plus an idempotent `generation_queue_schema` deploy one-shot update and migration/deploy/retention tests.

## Non-Goals

- Enabling or depending on Langfuse, or storing Langfuse inputs/outputs.
- Replaying raw structured logs, prompts, model responses, feedback or workflow payloads.
- Changing generation, retry, queue, recovery or review semantics.
- Building a general audit platform, a new scheduler, a new SSE stream, or an unbounded export API.
- Adding generation events to the synchronous initial `/workflow/start`, which has no `generation_runs` row; queued resume, recovery and autopilot runs are covered.

## Acceptance Criteria

- [x] AC1 Given a carousel generated through the queue, When its owner opens the workspace, Then newest runs show kind, queued/started/finished timestamps, attempts, status and error code, with phase outcomes and durations, image jobs, export and final status.
- [x] AC2 Given a failed and retried run, When the log renders, Then it shows the classified error code and retry without a raw exception message; recovery and a manually reprocessed run are also visible.
- [x] AC3 Given a non-owner non-admin or assigned reviewer, When they request the log, Then the API returns 403; anonymous requests return 401 and an unknown carousel returns 404; cross-project events never leak.
- [x] AC4 Given an exception containing a planted secret and a `DBAPIError` containing SQL and bound parameters, When failure events are recorded and read, Then neither stored rows nor API responses contain the secret, SQL or parameters, and details remain at or below 4096 serialized bytes.
- [x] AC5 Given an event store that raises or times out, When generation proceeds, Then the generation result is unchanged, safe warnings name only the event and exception types with timeout warnings rate-limited, and recorder latency is bounded and measured.
- [x] AC6 Given more than one page of events, When the owner loads more, Then keyset pagination returns no duplicates or omissions even when a newer event arrives, and every request is bounded to at most 200 events.
- [x] AC7 Given events older and newer than 30 days, When the existing daily purge runs, Then only expired events are removed in bounded batches and existing run/PgQueuer purges still complete on PostgreSQL.
- [x] AC8 Given an active run, When existing SSE or polling updates arrive, Then the timeline refreshes without a new interval and reaches its terminal state without SSE; older runs are collapsed, failures and warnings have non-color cues, durations are right-aligned, controls are keyboard accessible, and PT/EN strings exist.
- [x] AC9 Given Langfuse disabled or unavailable, Then generation and the log still work; given a real phase trace, Then its id and SDK-generated URL are stored and rendered as a link.

## Gherkin Scenarios

- `backend/tests/features/carousel_generation_log_ae0556.feature`
- `frontend/tests/features/create-generation-log-ae0556.feature`

## Delta

### ADDED

- Sanitized append-only generation events, a scoped recorder, paginated read API and workspace timeline.
- Event retention, trace links, migration and production one-shot coverage.

### MODIFIED

- Existing queue schema one-shot and daily purge include generation events.
- Existing queue/phase/image/export seams emit best-effort diagnostic events.

### REMOVED

- None.

## Affected Areas

- Backend: generation queue, carousel phase/image/export instrumentation, carousel routes and schemas.
- Frontend: create workspace data hook, sidebar timeline, schemas, API constants and locales.
- Database: new append-only table, indexes and cascading foreign keys.
- API: owner/admin generation-log page endpoint.
- Tests: unit, SQLite/PostgreSQL integration, migration/deploy and React behavior.
- Docs: this ticket, ADR-0028, architecture and delivery reports, OpenAPI.
- Prompts/LLM: none.
- Observability: safe persisted events and optional Langfuse trace links.
- Deployment: existing generation queue schema one-shot creates and verifies the new table/indexes.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: ADR-0026, AE-0553 safe failure logging, AE-0552 manual reprocessing, AE-0555 worker memory investigation.

## Implementation Plan

1. Commit the ticket, ADR, architecture plan and Gherkin; add failing recorder, store, API, migration and UI tests.
2. Implement bounded failure metadata, the scoped recorder and append-only model/store; instrument queue and phase attempts first.
3. Add image/export/notable-step events and optional SDK trace links.
4. Add the owner/admin paginated API, retention, Alembic and deploy one-shot.
5. Add the query hook and accessible PT/EN timeline using existing workflow updates.
6. Run targeted tests, lint and typecheck; measure recorder overhead; complete full non-mutation gates, external QA and CI.

## QA Checklist

- [x] Security reviewed
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-26

Development started after ticket validation and architecture validation passed. Dependencies and normal commit hooks are available in the ticket worktree.

Red-first event contracts failed at the missing recorder module. The bounded sanitizer, safe failure helper, scoped best-effort recorder and queue run/phase instrumentation now pass 20 targeted tests, including all pre-existing job-handler and recovery-isolation tests. Targeted Ruff lint passes.

The append-only model, owner/admin API, stable keyset pages, Alembic revision, existing deploy one-shot and 30-day purge are implemented. Dispatch/recovery, workflow outcome, phase score/gate, image bridge/reuse, PDF and optional Langfuse trace events are instrumented without raw generation content.

The workspace now has a cursor-paginated PT/EN timeline grouped by run and phase, native keyboard disclosures, older-run collapsing, text outcomes, safe detail summaries and optional trace links. Existing workflow updates invalidate the query; no timer or stream was added.

Independent QA research identified four concrete defects. Manual dispatch now records queued work, phase failures are written only after successful attempt-fenced transitions, fixed project attribution cannot be overwritten, and real empty API pages show the empty state. Additional hardening covers semantic detail bounds, image/export failures, equal timestamps, retention boundaries, migration cascades and future UI states.

Code research rejected existing run/audit/outbox data as a complete or safe timeline source. Pedro's requested behavior is specified as a new bounded, sanitized, best-effort event stream with 30-day retention and no Langfuse dependency.

### 2026-10-27

PR review follow-up at `40ec3b674` and `fc2597ec2`: terminal logs now refetch from the existing carousel capability poll after each successful update, including the active-to-terminal response, without relying on SSE or adding an interval. Repeated no-op autopilot and busy-lock attempts leave one waiting event per streak; real work records the resumed run boundary, while no-op steps leave no phase events. Immediate yields keep normal retry events and separate adjacent wait streaks.

Retention deletes expired events in batches of 50. Native disclosures no longer have a duplicate key handler, warnings have an icon and amber text, timeout warnings are rate-limited to one per 60 seconds, and resume helpers no longer import private cross-module names. The 0.962 ms measurement is p95 on disposable in-memory SQLite; production event writes are dropped at the 100 ms timeout without affecting generation.

Red-first regressions covered six no-op waits, five busy locks, wait/yield/wait separation, fresh yields, terminal refresh without SSE and three retention batches. Final focused run: 103 backend and 18 frontend tests pass. Full captures: backend 7804 passed, 2 skipped, 26 PASS / 0 FAIL / 1 CI-only mutation SKIP with 97% diff coverage; frontend 18 PASS / 0 FAIL / 1 CI-only mutation SKIP. Both integrity scans report zero blockers and warnings.

## Files Touched

- `.agent/active-task.md`, ticket, ADR-0028, architecture/plan/QA research and dev/QA reports.
- Backend migration, generation-queue domain/application/infrastructure/facades, carousel API schemas/routes, workflow/image/export instrumentation and OpenAPI snapshot.
- Backend Gherkin, queue/recovery/migration/API/unit/integration fixtures and tests.
- Frontend generation-log schema, query hook/types, workspace run/phase/event components and models, API constants, PT/EN locales, schema-drift map and Gherkin/tests.

## Test Evidence

- Red before implementation: `test_generation_events_ae0556.py` failed collection because the event application module did not exist.
- Core increment: 20 passed across the new event contracts, existing generation handler and recovery-isolation tests; after the no-op recorder adjustment, 16 event/handler tests passed again.
- Targeted Ruff lint: passed; Ruff format applied.
- Persistence/API increment: three new SQLite app tests pass for owner/admin/IDOR, stored-row sanitization, trace links and 200-event keyset pagination under concurrent insertion; 18 passed with the existing copy-version API regression suite.
- Rollout increment: 18 passed across queue-schema DDL/CLI, Alembic head plus upgrade/downgrade, and daily recovery/retention suites. The three new rollout tests were red before implementation for missing DDL, missing revision and missing purge.
- Instrumentation increment: 57 passed across notable-step, image-bridge, bilingual export, Langfuse phase trace and queue executor/dispatcher suites; 47 passed across workflow outcome and resume-runner suites.
- Frontend increment: 21 focused tests pass across cursor loading, update-driven invalidation without timers/streams, accessible timeline behavior, PT/EN, the workspace page and sidebar. Full `npm run lint` and `npm run typecheck` pass after splitting run/phase/event components.
- API/type evidence: backend strict mypy passes 1176 source files; OpenAPI regenerated and all 27 mapped frontend schemas report no drift.
- Recorder overhead: 200 real sequential inserts through sanitization, independent commits and the 100 ms timeout took 132.911 ms total; mean 0.650 ms, p50 0.660 ms, p95 0.962 ms, max 2.086 ms on disposable in-memory SQLite.
- PostgreSQL: 22 queue-schema/worker/retention tests plus the new keyset store test pass on disposable PostgreSQL 16. An initial fixture-only failure was fixed by creating the required `carousel_projects` parent table; production FK behavior was not weakened.
- Rebase and compatibility: `origin/main` advanced through PR #291, the page-cache release and the bridge-clock fix. All changes were replayed with the new attempt fencing preserved; recovery's richer DBAPI/SQLSTATE helper is reused. Final backend full capture: 26 PASS, 0 FAIL, 1 CI-only mutation SKIP.
- QA research fixes: manual-kick queue events, phase-failure writes only after a valid attempt fence, fixed-project scope, run-summary correlation, and the real one-page empty state were fixed. PgQueuer ids were removed from event details; detail inputs are capped and semantically constrained; missing image/export paths and unknown frontend states are covered.
- Expanded regressions: 191 backend tests and 23 frontend tests pass. Strict mypy passes 1202 files; import contracts, architecture ratchet, integrity, full frontend lint and typecheck pass. Final full frontend capture and external QA remain pending.
- External QA fixes: mismatched events are rejected on write and excluded on read; external image error codes map to safe classifications and models to canonical IDs; slide failures record before re-raise; raw strings are length-capped before normalization; outcome/attempt bounds match the DDL; artifact-only updates invalidate and terminal persistence triggers the existing run-finished refresh. Resume patch seams remain compatible and touched files stay under 400 lines.
- Latest regressions: 270 backend tests and 24 frontend tests pass; strict mypy passes 1205 files; full frontend lint and both integrity scans pass. Nullable autopilot correlation now uses the authoritative parent, terminal refreshes cover late assignment and failures with the correct reason, and the SQLite cascade fixture uses one connection. Batch dispatch uses the same parent hydration, and facades/test files are split below the 400-line limit.
- Confirmation regressions: 246 backend tests and 24 frontend tests pass; strict mypy passes 1206 files; import contracts and integrity remain green. Nullable autopilot correlation now uses the authoritative parent, terminal refreshes cover late assignment and failures with the correct reason, and the SQLite cascade fixture uses one connection. Batch dispatch uses the same parent hydration, and facades/test files are split below the 400-line limit.
- Final full backend capture: 7798 passed, 2 skipped; 26 PASS, 0 FAIL, 1 CI-only mutation SKIP; diff coverage 97%. Final full frontend capture: 18 PASS, 0 FAIL, 1 CI-only mutation SKIP. Independent implementation review found no remaining blockers; PR CI and backend mutation are pending for final QA signoff.

## QA Report

`.agent/reports/AE-0556.qa.md` — INCONCLUSIVE pending PR CI for `afd3c4424`. Independent follow-up review returned PASS after the wait/yield edge-case fix; all local full gates pass. Backend/frontend mutation and PR checks are the only remaining evidence.

## Decision Log

- 2026-10-26 (Pedro): use a new `carousel_generation_events` append-only table; existing generation runs lack phase history and existing audit/log payloads are not safe to copy.
- 2026-10-26 (Pedro): use direct one-row writes in independent short transactions with a 100 ms timeout, safe warning-only failure handling and no cross-run buffering or background task queue.
- 2026-10-26 (Pedro): details are a flat allowlisted object capped at 4096 serialized bytes; exception messages and all generation content are excluded. Safe localized messages come from event/message codes.
- 2026-10-26 (Pedro): retain events for 30 days through the existing daily purge; run and carousel deletion cascade to their events.
- 2026-10-26 (Pedro): paginate up to 200 events with an event-id keyset cursor and return only run summaries needed by that page.
- 2026-10-26 (Pedro): use the pinned Langfuse SDK's current trace id and `get_trace_url`; do not invent a URL or require Langfuse.
- 2026-10-27 (Pedro): use the existing carousel capability poll as the terminal-refresh fallback; in-process or relayed SSE remains only the immediate path.
- 2026-10-27 (Pedro): coalesce no-op and lock-busy waits to one persisted waiting event per streak and suppress their run/phase/retry noise; resumed real work closes the streak.
- 2026-10-27 (Pedro): batch retention deletes and rate-limit timeout warnings rather than changing the best-effort write contract.

## Blockers

None.

## Final Summary

Pending.
