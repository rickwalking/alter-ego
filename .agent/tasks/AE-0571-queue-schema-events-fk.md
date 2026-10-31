# AE-0571 — Queue schema one-shot fails on the events foreign key

Status: Done
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Developer
Branch: fix/ae-0571-queue-schema-fk
Created: 2026-10-27
Updated: 2026-10-27

## Goal

`python -m rag_backend.scripts.generation_queue_schema --apply --verify` exits 0 on every deploy.

## Problem

The deploy of main 19affecf failed in "Deploy to DigitalOcean via SSH": the one-shot raised
`NoReferencedTableError` for `carousel_generation_events.carousel_project_id -> carousel_projects`.
The deploy process imports only the queue models, so `carousel_projects` is not in the shared
metadata when the events DDL is compiled. Prod already has the table, its 3 indexes and both FKs;
the app is healthy, but every deploy fails the job.

## Scope

- Register the FK target model (`CarouselProjectModel`) before compiling the events DDL (lazy import: an eager one is circular).
- Tests: a bare-process compile (the case that hit prod), and Postgres apply+verify fresh and twice.

## Non-Goals

- Never drop or alter the existing table; no DDL change.

## Acceptance Criteria

- [x] The events DDL compiles in a fresh interpreter that imported only the schema module.
- [x] `--apply --verify` exits 0 on a fresh schema holding `carousel_projects` + `generation_runs`, creating the events table with both FKs and 3 indexes.
- [x] A second `--apply --verify` exits 0 and reports nothing missing.
- [x] `--verify` alone still exits 1 when the events table is missing.

## Repro Steps

1. `cd backend && uv run python -c "from sqlalchemy.dialects import postgresql; from rag_backend.modules.generation_queue.infrastructure.schema import generation_events_ddl; generation_events_ddl(postgresql.dialect())"`
2. Before the fix: `NoReferencedTableError`.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-27 21:00

Reproduced, fixed, tests added; hotfix fast path (mutation deferred to CI).

## Files Touched

- `backend/src/rag_backend/modules/generation_queue/infrastructure/schema.py`
- `backend/tests/features/generation_queue_schema_fk_ae0571.feature`
- `backend/tests/unit/scripts/test_generation_queue_schema_fk_ae0571.py`
- `backend/tests/integration/test_generation_queue_schema_fk_ae0571.py`

## Test Evidence

See `.agent/reports/AE-0571.dev-summary.md`.

## Final Summary

Merged to `main` in PR #302 (f475cfbd, 2026-10-28). The status was left open after the merge; closed on 2026-10-30 (ticket housekeeping, no code change).
