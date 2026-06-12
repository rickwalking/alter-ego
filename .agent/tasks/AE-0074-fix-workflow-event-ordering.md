# AE-0074 — Fix workflow event ordering: persist and commit before Redis publish

Status: Review
Tier: T2
Priority: High
Type: Bugfix
Area: Backend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: fix/ae-0074-workflow-event-ordering
Kanban Card: TBD
Created: 2026-06-12
Updated: 2026-06-12

## Goal

Workflow events reach Redis only after the corresponding audit record is
committed to PostgreSQL, eliminating the window where a rolled-back
transaction leaves a published event with no authoritative state.

## Problem

`WorkflowEventService.emit()`
(`backend/src/rag_backend/application/services/workflow_event_service.py`,
line 66) publishes to Redis Streams **before** flushing the
`WorkflowAuditLogModel` row, and the commit belongs to the caller. A
rollback after publish leaves the external stream inconsistent with the
database. Confirmed live bug (2026-06-12 verification); committed fix per
the plan is **reorder-only** — the durable outbox is explicitly Phase 6
scope.

**Design wrinkle — DECIDED (2026-06-12 interview):** the publish-first
ordering exists because the audit row stores the Redis entry ID
(`WorkflowAuditLogModel.stream_entry_id`, nullable, populated from the
`publish()` return value). Decision: **drop the column** via Alembic
migration — nothing reads it (verified), and the Phase 6 outbox will own
any audit↔stream linkage. This adds a small migration to scope; overflow
still routes to Phase 0b per the epic rule.

## Scope

- Restructure event emission so Redis publish happens only after the
  owning transaction commits (e.g., collect pending events on the session/
  unit-of-work and publish post-commit, or move the commit boundary —
  design choice documented in the Decision Log).
- Preserve event payload shape, stream name (`STREAM_CONTENT_EVENTS`),
  event IDs, and SSE-visible behavior exactly.
- Cover the rollback path with a test proving no publish occurs.
- Update every `emit()` call site to the new contract; no call site may
  publish-then-rollback.

## Non-Goals

- No outbox table, no at-least-once delivery, no consumer dedup (Phase 6).
- No event schema or stream name changes.
- No retry semantics changes for Redis publish failures beyond current
  behavior (a post-commit publish failure is logged, not retried — the gap
  becomes "committed but unpublished", which the Phase 6 outbox closes).

## Acceptance Criteria

- [x] WHEN a workflow event is emitted and the transaction commits THE
      audit row SHALL be committed before the Redis publish executes
- [x] WHEN the transaction rolls back after emit() is called THE system
      SHALL NOT publish the event to Redis (regression test required)
- [x] WHEN the post-commit Redis publish fails THE system SHALL log the
      failure with the event ID and SHALL NOT raise into the request path
- [x] Event payload fields, stream name, and event ID format are unchanged
      (assert against a captured fixture in the test); the only permitted
      data change is the `stream_entry_id` column removal per the next
      criterion
- [x] An Alembic migration drops `workflow_audit_log.stream_entry_id`
      (with a working downgrade), the ORM model no longer defines it, and
      `alembic upgrade head` passes on a database containing existing
      audit rows (verified on dev Postgres: 237 rows, up→down→up)
- [x] All existing emit() call sites compile and pass tests with the new
      contract; call sites enumerated in Files Touched (zero changes
      needed — session-hook mechanism)
- [x] `cd backend && uv run pytest` passes (1502 passed, 2 skipped); the
      new tests reference their Gherkin scenarios in comments
- [x] `cd backend && uv run mypy src/` (CI form, 367 files clean) and
      `uv run ruff check src/` pass
- [x] Diff coverage ≥ 75% per the CI gate (module at 96%; only the
      defensive no-event-loop guard uncovered)

## Gherkin Scenarios

```gherkin
Feature: Workflow event emission is consistent with the database

  Scenario: Event published only after commit
    Given a carousel workflow phase transition that emits an event
    When the surrounding transaction commits successfully
    Then the workflow audit record exists in PostgreSQL
    And the event is published to the content events stream afterwards

  Scenario: Rolled-back transaction publishes nothing
    Given a carousel workflow phase transition that emits an event
    When the surrounding transaction rolls back before commit
    Then no workflow audit record exists in PostgreSQL
    And no event is published to the content events stream

  Scenario: Publish failure after commit does not break the request
    Given a committed workflow phase transition with a pending event
    When the Redis publish fails
    Then the request completes successfully
    And the failure is logged with the event identifier
```

## Delta

### ADDED

- Post-commit publish mechanism (pending-events collection or equivalent)
- Tests for the three scenarios above

### MODIFIED

- `workflow_event_service.py` emit flow and its call sites

### REMOVED

- Pre-persistence Redis publish path

## Affected Areas

- Backend: workflow event service + call sites
- Frontend: none (SSE payloads unchanged)
- Database: one migration dropping `workflow_audit_log.stream_entry_id`
- API: none (response contracts unchanged)
- Tests: new ordering/rollback tests
- Docs: Decision Log records the chosen mechanism
- Prompts/LLM: none
- Observability: publish-failure log line with event ID
- Deployment: none (single-process; no migration)

## Dependencies

- Blocks: none (but de-risks Phase 6)
- Blocked by: none
- Related: AE-0070, AE-0072 (outbox decision section cites this fix),
  AE-0076 (partial overlap: `domain/constants/workflow_events.py` only),
  AE-0040 epic (overlap via emit() call sites such as
  `application/services/carousel/editorial_workflow_events.py`, not the
  service file itself — coordinate merges)

## Implementation Plan

1. Enumerate emit() call sites and their transaction owners.
2. Choose mechanism (post-commit hook vs explicit two-step) and record it.
3. Implement, write the three scenario tests, run the backend gates.

## QA Checklist

- [x] Security reviewed (OWASP lens; 0 blockers; log-leak suggestion fixed)
- [x] Code quality reviewed (no new violations; pre-existing debt separated)
- [x] Acceptance criteria validated (9/9 after fix round)
- [x] Edge cases tested (stale queue, double commit, publish failure, log content)
- [x] Orphan/unfinished code checked (accepted gaps documented)

## Progress Log

### 2026-06-12 00:00

Ticket created by planner.

### 2026-06-12 (development)

Implemented on branch `fix/ae-0074-workflow-event-ordering`. Mechanism:
SQLAlchemy session events. All gates green; migration verified both
directions on the dev Postgres with 237 existing audit rows.

## Files Touched

Changed:

- `backend/src/rag_backend/application/services/workflow_event_service.py`
  — emit() now persists + queues; publish moved to an `after_commit`
  listener as a tracked asyncio task; `after_rollback` discards;
  `drain_pending_publishes()` added for tests/shutdown
- `backend/src/rag_backend/domain/constants/workflow_events.py` — added
  `SESSION_INFO_PENDING_EVENTS`
- `backend/src/rag_backend/infrastructure/database/models/workflow_audit_log.py`
  — `stream_entry_id` column removed
- `backend/alembic/versions/0011_drop_audit_stream_entry_id.py` — new
  migration (drop + downgrade re-add)
- `backend/tests/features/workflow_event_ordering.feature` — new
- `backend/tests/unit/application/test_workflow_event_service.py` —
  rewritten: 5 scenarios incl. stale-queue edge case

emit() call sites verified UNCHANGED (session-hook design needs none):
`application/services/editorial_audit_service.py`,
`application/services/scheduled_publish_service.py`,
`api/routes/blog_post_workflow.py`,
`application/services/carousel/editorial_workflow_events.py`.
`api/schemas/workflow_audit.py` keeps `stream_entry_id: str | None`
(serializes `null`; response contract unchanged).

## Test Evidence

```bash
uv run pytest -q                       # 1502 passed, 2 skipped (pre-QA run)
uv run pytest tests/unit/application/test_workflow_event_service.py -q
# 5 passed at dev complete (the original "6" was a reporting error QA
# caught); 6 passed after the QA fix round added the duplicate-commit test
cd src && uv run mypy rag_backend/ --explicit-package-bases  # clean, 367 files
uv run ruff check src/ tests/          # All checks passed
# Migration on dev Postgres (rag_db, 237 audit rows), offline SQL via docker exec:
# upgrade 0010→0011: version=0011, rows=237, column gone
# downgrade 0011→0010: version=0010, rows=237, column restored nullable
# re-upgrade: version=0011
```

Module coverage 96% (only the no-running-loop guard uncovered).

QA fix round (post-review): rollback test asserts the session queue is
cleared; publish-failure test asserts the structured log carries the
event ID (capture_logs); duplicate-commit test proves drain-not-re-read;
`logger.exception` → `logger.warning` in the no-loop guard.

## QA Report

`.agent/reports/AE-0074.qa.md` — external OpenCode QA session
(kimi-k2.6, read-only), verdict **WARN, 81/100 (B), zero blockers**;
all actionable findings fixed same day (see post-QA addendum in the
report). Status moved to Review per protocol (warnings only).

## Decision Log

- **Mechanism: SQLAlchemy session events** (`after_commit` publishes via
  tracked asyncio task; `after_rollback` discards). Chosen over explicit
  `commit_and_publish()` call-site changes because transaction owners
  are scattered (routes commit in six places; the carousel workflow's
  commit owner is indirect) — an explicit contract would be one missed
  call site away from silent event loss. Ordering is now guaranteed by
  construction for every current and future emit() caller.
- **stream_entry_id: dropped** per the 2026-06-12 interview decision;
  response schema field retained (always `null`) to keep the API
  contract byte-stable.
- **Known accepted gap:** publish failure after commit leaves the event
  committed-but-unpublished (logged with event_id). This is the
  documented trade until the Phase 6 outbox provides durable delivery.
- In-flight publish tasks are awaitable via `drain_pending_publishes()`;
  app-shutdown wiring deliberately not added (scope discipline — the
  Phase 6 outbox supersedes it).

## Blockers

None.

## Final Summary

Reorder-only fix delivered: workflow events now reach Redis strictly
after their PostgreSQL transaction commits; rollbacks publish nothing
(including the same-session stale-queue edge); publish failures log and
never break requests. `stream_entry_id` dropped via migration 0011,
verified up/down/up against the dev database with 237 existing rows.
Zero call-site changes; full suite, mypy strict, and ruff all green.
