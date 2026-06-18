# AE-0212 — Emit traceback for workflow_workers_error (call-site exc_info)

Status: Intake
Tier: T1
Priority: Medium
Type: Bug
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

`workflow_workers_error` must log a traceback so the recurring worker failure can be diagnosed.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`infrastructure/logging.py:35` includes `structlog.processors.format_exc_info` (works — `carousel_image_generation_failed` logs a full traceback). But `application/workers/workflow_workers.py:53` `logger.exception("workflow_workers_error")` emits the event with **no `exception` field** (prod, every 60s). The bare structlog BoundLogger call isn't binding `exc_info`.

## Scope

- Fix the call site to emit the traceback (`exc_info=True` or proper binding) at `workflow_workers.py:53`.
- Diagnose + fix the underlying scheduled-publish/reminders/alert worker error surfaced by the traceback.
- Guard: a test asserting the worker error path renders `exc_info`.

## Non-Goals

- Rewriting the global structlog config (already correct).

## Acceptance Criteria

- [ ] `workflow_workers_error` log events include a traceback.
- [ ] The underlying recurring error is identified and fixed (no longer fires every 60s).
- [ ] Test asserts the exception is rendered.

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: —

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
