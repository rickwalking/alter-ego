# AE-0541 — Checkpoint prune: queued, running and dead-letter generation runs protect their thread

Status: In Development
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0541-prune-generation-runs-guard
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-30

## Goal

Once the carousel generation queue lands, the signed-off checkpoint prune never matches a carousel that still has a
generation run waiting, running or held in its queue.

## Problem

The prune (AE-0525) keeps a carousel's whole checkpoint history while the project is running, has a pending
republish, or has an autopilot run that is not settled (`published`, `rejected`, `expired`). The queue (AE-0522)
adds `generation_runs`; a run in `queued`, `running`, `retry_wait` or `dead_letter` resumes the LangGraph thread
from its checkpoint. That table is not on `main` yet, so the prune cannot check it. Without this guard a
dead-lettered run on an old, published carousel could be matched (keep-latest still keeps the latest checkpoint, but
Pedro asked that a queued, running or held run keep its full history).

## Scope

- `backend/src/rag_backend/infrastructure/database/checkpoint_prune.py` `_eligible_projects`: a project with a
  `generation_runs` row in a non-terminal state (queued, running, retry_wait, dead_letter; the exact names from
  AE-0522) is not eligible, in the dry run and in the locked re-check of `--apply`.
- The state list comes from AE-0522's state enum, not string literals.

## Non-Goals

- Any change to the queue itself.

## Acceptance Criteria

- [x] AC1 Given a published carousel past the TTL with a generation run in each non-terminal state, When the prune
  dry-runs, Then none of them is listed; a carousel whose only run succeeded is listed.
- [x] AC2 Given a signed-off thread whose carousel gets a queued generation run after the dry run, When the prune
  applies, Then it refuses and deletes nothing.

## Gherkin Scenarios

Extend `backend/tests/features/checkpoint_prune_ae0525.feature` ("A carousel whose generation run is queued, running
or held is never matched").

## Dependencies

- Blocked by: AE-0522 (the `generation_runs` table on `main`) — merged in #275; unblocked 2026-10-30.
- Related: AE-0525.

## Decision Log

- 2026-10-24: split out of AE-0525 because `generation_runs` is not on `main` yet; Pedro asked that it join the
  eligibility check as soon as the queue lands.

## Blockers

AE-0522 not merged.
- 2026-10-30: the held states are `generation_queue.constants.HELD_STATUSES` = the queue's `ACTIVE_STATUSES` (queued,
  running, retry_wait) plus `dead_letter`; `succeeded` and `cancelled` never resume the thread. The prune asks the
  queue through its public facade (`generation_queue.public.project_has_held_run`), the same `EXISTS` shape as the
  existing `project_has_active_run`, so the import-linter boundary stays intact. Pedro asked for the queue tickets
  before the users-area items (2026-10-30).

## Progress Log

- 2026-10-30: guard added to `_eligible_projects` (dry run and the locked `--apply` re-check share it); two Gherkin
  scenarios and two Postgres integration tests; both tests fail with the guard removed and pass with it.

## Files Touched

- `backend/src/rag_backend/modules/generation_queue/constants.py` (`HELD_STATUSES`)
- `backend/src/rag_backend/modules/generation_queue/public.py` (`project_has_held_run`, shared `_project_has_run_in`)
- `backend/src/rag_backend/infrastructure/database/checkpoint_prune.py` (eligibility guard + module docstring)
- `backend/tests/features/checkpoint_prune_ae0525.feature` (2 scenarios)
- `backend/tests/integration/checkpoint_prune_pg_support.py` (`generation_runs` table, `seed_generation_run`)
- `backend/tests/integration/test_checkpoint_prune_pg_ae0525.py` (2 tests)

