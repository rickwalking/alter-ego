# AE-0617 — A final-review refresh runs ahead of queued full drives

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0617-review-refresh-priority
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

A one-click change at the final review brings the new Telegram review back in minutes, not after every full
generation drive that was queued first.

## Problem

Production, 2026-11-04: refresh drive 5420ce53 for carousel 9aaf2096 was staged at 12:41:57Z. It only needed the
cheap final-review stop, but it sat FIFO behind drive e6c42a34 (run d5bd6107, running since 12:39:37Z) and a queued
drive for run 77a6593b on the single generation worker. A full drive takes about 30-35 minutes, so the owner's new
approve message came more than an hour after a one-click change. AE-0597 says "the worker sends the review again"
with no latency goal; the hour was never intended.

## Findings

- A `reworking` run gets a full `autopilot_drive` from the dispatcher's safety net at ordinary priority
  (`dispatcher.py` `_stage_missing`, `queue_bridge.py` `active_run_ids`). The only raised priority was manual
  reprocess (`MANUAL_REPROCESS_PRIORITY`, carried in `PAYLOAD_MANUAL_PRIORITY`). PgQueuer orders by
  `priority DESC, id ASC` and the gateway honours the payload priority, so queue order is plain FIFO for this work.
  Root cause confirmed.
- Deciding the priority only when the drive is staged is not enough. A website cover hold puts the run in
  `reworking` with the `website_cover` marker, and the dispatcher stages its drive within 10 s, before the switch
  releases the hold. The drive exists at ordinary priority by the time the run becomes a refresh, and `stage` is a
  no-op on its dedupe key. A drive that is already waiting has to be raised as well.
- The hand-over order (`repository.py` `undispatched`, FIFO) does not decide the pick: the priority on the PgQueuer
  job does. A pass hands over 20 rows every 10 s, so the hand-over does not need changing.
- `review_reopened` (editorial facade) already answers "a completed draft waiting in final review, not released".
  A revise under way fails it (the row left final review), so it tells a refresh from a drive that still has
  content work to do.

## Scope

- The dispatcher stages a refresh drive at `REVIEW_REFRESH_PRIORITY`, and raises a drive of that run that already
  waits (queued or retry_wait), keeping its job, its FIFO place in the class and any retry delay.
- `AutopilotQueueBridge.review_refresh_run_ids` lists the runs whose only remaining work is the refresh.

## Non-Goals

- No pre-emption, no timeout, limit, worker-count or gate change, no production data change.
- No change for other work: new drives, content reworks, "Fix issues" and "Usar capa do Grok" stay FIFO at ordinary
  priority.

## Acceptance Criteria

- [ ] A refresh drive is picked before older ordinary drives on real PgQueuer.
- [ ] A drive staged before the run became a refresh is raised on a later pass, and keeps any retry delay.
- [ ] A running drive is never interrupted or changed; the refresh runs next.
- [ ] A rework with work left (content revise, autofix, GrokBot cover, active hold, revise under way) keeps FIFO.
- [ ] Failing tests were recorded before the fix.

## Gherkin Scenarios

`backend/tests/features/review_refresh_priority_ae0617.feature`.

## Delta

### ADDED

- `REVIEW_REFRESH_PRIORITY`, `WAITING_STATUSES`, `review_refresh_stage`, `review_refresh_run_ids`,
  `GenerationRunStore.raise_priority`, `JobQueue.raise_priority`.

### MODIFIED

- `Dispatcher._stage_missing` handles refreshes first. ADR-026 records the new priority-class member.

### REMOVED

- Nothing.

## Affected Areas

- Backend: `modules/generation_queue`, `modules/autopilot/queue_bridge.py`
- Frontend: none (the queue board already sorts by priority)
- Database: none (the priority lives in the existing payload)
- API: none
- Tests: unit, SQLite bridge, Postgres + PgQueuer
- Docs: ADR-026
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0597, AE-0552

## Implementation Plan

1. `.feature` and failing tests.
2. Bridge read, staging, store and queue raise, dispatcher.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04 14:00

Ticket created, root cause verified in code.

### 2026-11-04 16:00

Fix, tests and ADR note done; PR opened.

## Files Touched

- `backend/src/rag_backend/modules/autopilot/queue_bridge.py`
- `backend/src/rag_backend/modules/generation_queue/`: `application/dispatcher.py`, `bootstrap.py`, `constants.py`,
  `domain/models.py`, `domain/ports.py`, `infrastructure/pgq_gateway.py`, `infrastructure/repository.py`
- `backend/tests/features/review_refresh_priority_ae0617.feature`, four new `*_ae0617.py` test files, `queue_fakes.py`
- `docs/decisions/0026-carousel-generation-queue.md`

## Test Evidence

- Red, with `dispatcher.py` at main and the other plumbing in place: 8 failed, 8 passed in the dispatcher and Postgres
  files. The real PgQueuer failures include `test_a_new_refresh_is_picked_before_older_drives`,
  `test_a_drive_staged_earlier_is_raised_and_keeps_its_job` and `test_a_running_drive_is_not_interrupted`.
  `test_a_rework_with_work_left_keeps_fifo` and the running-refresh test pass on main, as guards should.
- Green: 33 passed across the four new files; 311 + 1 across `tests/unit/modules/generation_queue` and the bridge,
  manual-kick and queue Postgres files.
- `backend:test`: 8863 passed, 2 skipped, 1 failed. The failure is `test_check_env_permissions.py::
  test_fires_on_wrong_owner_expectation`: it expects a non-root runner and this host runs as uid 0. This branch does
  not touch that script or test.
- `backend:diff-cover` PASS (100%). 18 cheap gates PASS: format, lint, lint-diff, blanket-ignore, strict-diff, type,
  imports, arch-ratchet, docstrings, dead-code, inline-prompts, gherkin-refs, comments, redis-factory, autopilot-env,
  openapi-fresh, integrity, duplication.
- Full gate: lead's heavy slot.

## QA Report

Pending.

## Decision Log

- **Same value as manual reprocess, under its own name.** `REVIEW_REFRESH_PRIORITY = MANUAL_REPROCESS_PRIORITY`
  (1). A refresh takes seconds, so sharing the class costs a manual reprocess almost nothing, and a higher class
  would let refreshes overtake the owner's explicit recovery for no gain. FIFO holds within the class.
- **Only `rework_phase IS NULL` at final review counts as a refresh.** A queued content revise regenerates phases;
  "Fix issues" can call a model; "Usar capa do Grok" switches and renders slide 1. They do more than the stop, and
  letting them jump would make a full drive wait behind real work with no owner decision. They keep FIFO. An active
  website cover hold is left ordinary as well: it has nothing to do until released, and the first pass after the
  release raises it.
- **An approved-meanwhile carousel stays ordinary.** `review_reopened` excludes it, this path is rare, and its
  review is not what the owner is waiting for.
- **A raise is never undone.** The gateway's rule is "without demotion". A run in `reworking` cannot take an owner
  rework tap, so a raised drive does not gain work while it waits.
- **The raise keeps `execute_after`.** The manual accelerate resets it; here that would turn a 60-second render wait
  into a poll on every 10-second pass.
- **The priority is a hint, not a guard.** A stale read can at worst put one drive early; the drive's own decisions
  do not read it.

## Blockers

None.

## Final Summary

Pending.
