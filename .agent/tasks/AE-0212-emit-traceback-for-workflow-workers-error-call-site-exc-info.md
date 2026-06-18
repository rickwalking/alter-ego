# AE-0212 — Emit traceback for workflow_workers_error (call-site exc_info)

Status: Dev Complete
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

- [x] `workflow_workers_error` log events include a traceback.
- [~] The underlying recurring error is identified and fixed (no longer fires every 60s). — Root cause not reproducible from code in CI/local (no live prod DB); strongest suspect documented (prod schema drift). The traceback fix now surfaces the real cause in prod logs.
- [x] Test asserts the exception is rendered.

## Repro Steps

1. ...

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: —

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

### 2026-06-18 — In Development (worktree feat/kz-workers)

Confirmed root cause: working call sites (e.g. `images.py:258`) pass
`exc_info=True` explicitly; `workflow_workers.py:53` `logger.exception(...)`
alone bound no `exc_info`, so `format_exc_info` had nothing to render. Fixed the
call site to `logger.exception("workflow_workers_error", exc_info=True)`. Added a
seeded test that renders the worker log through the real `format_exc_info`
pipeline and asserts the traceback is present; verified it FAILS without the fix
(no `exception` field) and PASSES with it.

Underlying recurring failure: not reproducible from code (no live prod DB
locally/CI). Strongest suspect is prod DB schema drift — prod is bootstrapped via
`create_all` with no Alembic, so a column added to `CarouselProjectModel` (e.g.
`is_public`, `workflow_status`, `presentation_policy_*`, `artifact_version`,
`slide_layout_strategy`) but absent in prod makes `select(CarouselProjectModel)`
in the alert/auto-reject queries raise `UndefinedColumn` every tick. The
traceback now surfaces the exact cause in prod logs for a definitive fix.

### 2026-06-18 — Dev Complete

Status → Dev Complete.

## Files Touched

- `backend/src/rag_backend/application/workers/workflow_workers.py` (call-site `exc_info=True`)
- `backend/tests/unit/application/test_workflow_workers.py` (seeded traceback test)
- `backend/tests/features/workflow_never_stuck.feature` (Gherkin)

## Test Evidence

```bash
uv run pytest tests/unit/application/test_workflow_workers.py -q   # 1 passed
# negative control: revert exc_info=True -> assert "exception" in output FAILS
```

## QA Report

Pending.

## Blockers

None.
