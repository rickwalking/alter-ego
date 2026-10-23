# AE-0525 — P3b — safe LangGraph checkpoint pruning (AE-0342 fix)

Status: In Development
Tier: T2
Priority: Medium
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0525-checkpoint-pruning
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-23

## Goal

Fix the never-matching checkpoint TTL/prefix so old checkpoints of published/rejected projects are pruned, with safety rails because deletion is irreversible.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Root cause (AE-0342): `backend/scripts/cleanup_carousel_checkpoints.py` targets `carousel-{id}` thread ids while the
  workflow keys checkpoints by the bare project id, so it never matched a row; it was also never scheduled. Replace it
  with one shared `checkpoint_thread_id()` used by the workflow engine and the prune.
- New guarded CLI `python -m rag_backend.scripts.checkpoint_prune`: dry run by default; `--apply` needs Pedro's
  signed-off thread list and a backup file, re-checks eligibility under a row lock, and deletes in one transaction.
- Keep-latest pruning: each thread keeps its latest checkpoint (per namespace), the writes of that checkpoint and of its
  parent, and the blobs it references; everything older goes. The workflow state API reads only the latest
  checkpoint, so a pruned carousel still opens; a full thread delete would 404 its workflow view.
- Eligible projects: finished (`completed`/`failed`), last updated before the TTL (`carousel_checkpoint_ttl_days`),
  not running, no pending republish, no autopilot run that is not settled (only `published`, `rejected` and `expired`
  runs are settled; queued, generating, owner-wait, rework, scheduled, publishing and held/failed runs protect the
  thread), and rejected or published. Threads without a carousel project are never touched
  (they may belong to another graph).

## Non-Goals

- Any change to the queue or the daily scan. Scheduling the prune (each run needs Pedro's sign-off). The runaway-thread
  size alarm of AE-0342.

## Acceptance Criteria

- [ ] AC1 Given a dry run, Then it lists the matched thread ids with their projects' states and the rows each table
  would lose, and deletes nothing.
- [ ] AC2 Given Pedro's sign-off and a backup, When the prune runs, Then only the signed-off threads are pruned and the
  checkpoint tables shrink accordingly; the backup holds every deleted row.
- [ ] AC3 Given a pruned thread, Then its workflow state (values, next node, pending interrupt) is the same as before.
- [ ] AC4 Given a signed-off thread that is no longer eligible (resumed, republish pending, an autopilot run queued,
  too recent, not a carousel), Then the prune refuses and deletes nothing.
- [ ] AC5 Given signed-off threads with removable rows, When nothing is deleted, Then the run exits non-zero (no silent
  no-op), and the log reports deleted counts per table.
- [ ] AC6 The workflow engine and the prune build the thread id with the same function.
- [ ] AC7 Given a carousel whose autopilot run is queued, running or held, Then it is never matched; and a pruned
  thread parked at a human gate still resumes from that gate to the end.

## Gherkin Scenarios

`backend/tests/features/checkpoint_prune_ae0525.feature`.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-23: keep-latest instead of a full thread delete, so the workflow view of a pruned carousel keeps working;
  orphan threads are excluded; the prune is a manual, signed-off CLI, not a scheduled job.
- 2026-10-23: a project with an autopilot run that is not settled (published, rejected, expired) is never eligible,
  so a queued, running or held run keeps its full checkpoint history. The `generation_runs` table of the queue
  (AE-0522) is not on `main` yet; once it lands, its queued/running/dead-letter runs must join this guard.
- 2026-10-23: independent QA (PASS) follow-ups: `--ttl-days` below 1, a missing sign-off file and an existing backup
  file are usage errors before any database access; the backup is created owner-only; a unit test fails if the
  carousel graph adopts a `DeltaChannel` (keep-latest would cut the history it is rebuilt from). Runbook:
  `docs/deployment/checkpoint-prune-runbook.md`.
