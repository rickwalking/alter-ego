# AE-0584 — Boost request returns 409: the first status event is inserted before its request

Status: Done
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0584-boost-insert-order
Kanban Card: TBD
Created: 2026-10-31
Updated: 2026-10-31

## Goal

`POST /api/autopilot/boost-request` stores a pending request and notifies the owner on Postgres, instead of answering
409 "Conflict".

## Problem

Both of the bot's boost requests on prod (2026-10-31 ~16:06Z) got HTTP 409 "Conflict"; nothing was stored and no
Telegram notice went out. `SqlBoostStore.insert` added the request row and its first `boost_request_events` row and
flushed once. The two models share only a foreign key (no `relationship()`), so SQLAlchemy did not order the INSERTs
and wrote the event first. Postgres rejected it (`ForeignKeyViolationError` on
`boost_request_events_request_id_fkey`), and the global `IntegrityError` handler mapped that to 409. The transaction
rolled back, and the owner notice only runs after commit. Every boost test used in-memory fakes or SQLite (no FK
enforcement), so the store had never run on Postgres. The prod schema matches migration `a8b9c0d1e2f3` exactly (not
drift).

## Scope

- `SqlBoostStore.insert` flushes the request row before adding its first event.
- Postgres integration tests for the store through the service: create (one row, one event, owner notified), owner
  approval (second event), idempotent replay (no second row or event).

## Non-Goals

- Caps, the approval flow, the API contract or the generic 409 response (the handler already logs `integrity_error`
  with the database message server-side).

## Acceptance Criteria

- [x] AC1 A boost request on Postgres is stored as pending approval with one event, and the owner is notified.
- [x] AC2 The owner's approval on Postgres stores the approved status and a second event.
- [x] AC3 The same idempotency key replays the stored request without a second row, event or notice.
- [x] AC4 The new tests fail on the old store with the same foreign key violation seen on prod.

## Gherkin Scenarios

- `backend/tests/features/boost_store_postgres_ae0584.feature`

## Repro Steps

1. Postgres with the boost tables, an eligible `ig_media` row.
2. `BoostRequestService.create` with `SqlBoostStore` → `IntegrityError` (FK violation) → 409.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-31

Root cause reproduced on local Postgres; prod schema checked against the migration (identical, 0 rows). Other stores
checked: the only other multi-row flushes are audit + outbox pairs, which have no foreign key between them.
Fix and tests written: 3 passed with the fix; on the old store all fail with the FK violation.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/infrastructure/boost_store.py`
- `backend/tests/integration/test_boost_store_pg_ae0584.py`
- `backend/tests/features/boost_store_postgres_ae0584.feature`

## Test Evidence

Full local backend gates at bf8481d9: pass 26, fail 0, skip 1 (mutation, CI only). GATES_JSON in
`.agent/reports/AE-0584.dev-summary.md`. The three Postgres tests pass with the fix and fail on the old store with the
prod foreign key violation; PR CI ran them (PASSED).

## QA Report

Root cause reproduced on Postgres; sweep of other stores found no other parent and child added in one flush.

## Blockers

None.

## Final Summary

Merged to `main` in PR #319 (85f4652b, 2026-10-31): a boost request stores its row before its first event, so the
bot's request is accepted (202) instead of 409. Deployed and verified read-only; the bot resends with the same keys.
