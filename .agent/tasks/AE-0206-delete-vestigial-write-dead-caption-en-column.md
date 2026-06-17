# AE-0206 — Delete vestigial write-dead caption_en column

Status: Intake
Tier: T1
Priority: Low
Type: Task
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Delete the **write-dead** `caption_en` column from `carousel_projects`. Nothing
produces it; it is only an ORM mirror of a producer-less domain field, read once.
No canonical home is needed (no data to preserve) — this is pure removal.

## Problem

The cold-critic review (2026-06-17) found `caption_en` has **no producer
anywhere** — it is assigned only via ORM `from_entity`/`update_from_entity`
mirroring a domain field that nothing sets, and read once in
`carousel_template/html_template.py:111`. Giving it a canonical home (per AE-0204)
would be gold-plating; it should simply be deleted.

## Scope

- Remove the `caption_en` read in `html_template.py` (it is effectively always
  empty; fall back to `caption` / empty string — behavior-preserving).
- Remove the ORM column + the domain-field mirror in `from_entity`/`update_from_entity`.
- Destructive Alembic migration to drop the column (downgrade re-adds nullable).
- Defensive `pg_dump` backup (expected empty).

## Non-Goals

- The other five embedded columns.

## Acceptance Criteria

- [ ] No code references `caption_en` (word-boundary grep clean).
- [ ] Migration drops the column; `downgrade` re-adds `nullable=True`; round-trips.
- [ ] Backend tests + EN carousel render unaffected (column was empty).
- [ ] Defensive `pg_dump` taken (confirm empty before drop).

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Blocks: (none)
- Blocked by: (none — independent; no data to preserve). Still destructive →
  consent-gated, but lowest risk of the group.
- Related: AE-0162, AE-0205

## Progress Log

### 2026-06-17 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
