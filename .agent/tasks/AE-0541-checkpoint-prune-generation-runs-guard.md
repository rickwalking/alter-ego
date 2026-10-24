# AE-0541 — Checkpoint prune: queued, running and dead-letter generation runs protect their thread

Status: Blocked
Tier: T1
Priority: Medium
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-24

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

- [ ] AC1 Given a published carousel past the TTL with a generation run in each non-terminal state, When the prune
  dry-runs, Then none of them is listed; a carousel whose only run succeeded is listed.
- [ ] AC2 Given a signed-off thread whose carousel gets a queued generation run after the dry run, When the prune
  applies, Then it refuses and deletes nothing.

## Gherkin Scenarios

Extend `backend/tests/features/checkpoint_prune_ae0525.feature` ("A carousel whose generation run is queued, running
or held is never matched").

## Dependencies

- Blocked by: AE-0522 (the `generation_runs` table on `main`).
- Related: AE-0525.

## Decision Log

- 2026-10-24: split out of AE-0525 because `generation_runs` is not on `main` yet; Pedro asked that it join the
  eligibility check as soon as the queue lands.

## Blockers

AE-0522 not merged.
