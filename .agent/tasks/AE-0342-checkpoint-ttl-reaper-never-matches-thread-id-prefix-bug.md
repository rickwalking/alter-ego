# AE-0342 — the checkpoint TTL reaper has never deleted anything (thread-id prefix mismatch)

Status: Ready
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

Make the carousel checkpoint TTL cleanup actually reap. Checkpoint tables must not
grow without bound, and the job must prove it deleted something rather than
reporting success on a query that matches nothing.

## Problem

`backend/scripts/cleanup_carousel_checkpoints.py` builds its target thread ids
with a `carousel-` prefix:

```python
return [f"carousel-{row[0]}" for row in result.fetchall()]   # _collect_stale_thread_ids
```

But the workflow keys checkpoints by the **bare project id**:

```python
configurable: dict[str, object] = {"thread_id": project_id}   # carousel_workflow_engine.py:64
```

and the ACL documents the same invariant (`thread_id == project_id`,
`legacy_carousel_acl.py:83-86`).

Measured on prod (2026-09-15):

```
SELECT count(*) FILTER (WHERE thread_id LIKE 'carousel-%') AS prefixed,
       count(*) FILTER (WHERE thread_id NOT LIKE 'carousel-%') AS bare,
       count(DISTINCT thread_id) FROM checkpoints;
-> prefixed = 0 | bare = 20205 | threads = 30
```

**Zero** rows carry the prefix. The reaper has therefore never deleted a single
checkpoint since it was written — it iterates a list of thread ids that match
nothing, deletes nothing, and logs a successful run. Silent no-op.

The cost was paid this month: the AE-0330 graph-loop defect left a single thread
with 701,030 `checkpoint_writes` rows and the database at **1429 MB**, of which
1407 MB was checkpoint tables. That had to be pruned by hand
(`DELETE … WHERE thread_id = 'dcaa5fef-…'` + `VACUUM FULL`, database now 27 MB).
A working reaper would have capped the ordinary growth; it would not have caught
the runaway, which is why the second half of this ticket adds a size alarm.

## Scope

- Fix `_collect_stale_thread_ids` to emit the bare project id (or centralize the
  thread-id construction so producer and reaper share one function — preferred,
  since the duplicated literal is the root cause).
- Make the job **fail loudly on a no-op**: if there are finished projects past the
  TTL and zero rows were deleted, log an error / exit non-zero rather than
  reporting a clean run.
- Report deleted counts per table in the job's log line.
- Add a guard/alert on checkpoint table size or per-thread row count, so a runaway
  thread (the AE-0330 class) is caught while it is happening rather than at 791 MB.
- Confirm the job is actually scheduled in prod; if it is not, that is part of why
  growth was unbounded.

## Non-Goals

- Fixing the graph loop that produced the runaway (already fixed in AE-0330).
- Changing the TTL value.
- Migrating checkpoint storage.

## Acceptance Criteria

- [ ] The reaper deletes checkpoints for a finished project past the TTL —
      proven by a test that seeds a finished project with checkpoint rows and
      asserts they are gone.
- [ ] Thread-id construction is shared between the workflow engine and the reaper
      (one function, no duplicated prefix literal); a test asserts they agree.
- [ ] A run that finds stale projects but deletes nothing reports an error
      instead of success.
- [ ] Per-table deleted counts appear in the run log.
- [ ] A size/row-count alarm fires for a thread far above the normal range
      (normal here is ~200-400 writes per thread; the runaway was 701,030).
- [ ] The job's schedule in prod is confirmed and documented.

## Gherkin Scenarios

```gherkin
Feature: Checkpoint TTL cleanup actually reaps

  Scenario: A finished project past the TTL is reaped
    Given a completed carousel project older than the TTL
    And checkpoint rows exist for its thread
    When the cleanup job runs
    Then those checkpoint rows are deleted
    And the deleted counts are logged

  Scenario: A recent project is untouched
    Given a completed carousel project newer than the TTL
    When the cleanup job runs
    Then its checkpoint rows remain

  Scenario: A silent no-op is reported as a failure
    Given stale projects exist
    And the delete matches no rows
    When the cleanup job runs
    Then it exits non-zero with an explicit error

  Scenario: A runaway thread raises an alarm
    Given one thread holds far more checkpoint writes than the normal range
    When the size guard evaluates
    Then an alarm is raised naming the thread
```

## Affected Areas

- Backend: `backend/scripts/cleanup_carousel_checkpoints.py`, `agents/carousel_workflow_engine.py` (shared id helper)
- Frontend: no
- Database: checkpoint tables (growth)
- API: no
- Tests: reaper integration test + producer/reaper agreement test
- Docs: deployment/ops — the job's schedule
- Prompts/LLM: no
- Observability: deleted counts, runaway alarm
- Deployment: cron/schedule confirmation

## Dependencies

- Blocks: bounded database growth
- Blocked by: none
- Related: AE-0330 (the runaway loop that exposed this)

## Implementation Plan

1. Test that seeds a stale finished project with checkpoint rows and asserts the
   reaper deletes them (fails today).
2. Extract a single `checkpoint_thread_id(project_id)` helper; use it in both the
   engine and the reaper; assert agreement in a test.
3. Add the no-op-is-a-failure check and the per-table counts.
4. Add the runaway size guard with a seeded-violation test (AE-0180).
5. Confirm and document the prod schedule.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (no stale projects at all; project finished exactly at the TTL boundary)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created during the AE-0330 handoff follow-up, while pruning the runaway
thread by hand. The prefix mismatch was found by querying prod directly:
0 of 20,205 checkpoints carry the `carousel-` prefix the reaper looks for.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
