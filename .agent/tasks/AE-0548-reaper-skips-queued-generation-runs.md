# AE-0548 — The stale-run reaper leaves projects with a queued generation run alone

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: QB
Branch: fix/ae-0548-reaper-skips-queued
Created: 2026-10-25
Updated: 2026-10-25

## Goal

A dashboard resume waiting in the generation queue is never reaped, so the owner's open tab keeps its lock version.

## Problem

Seen on prod during the AE-0522 production validation (2026-10-25). With `GENERATION_WORKER_CONCURRENCY` 1, Pedro's
dashboard resumes on project `2fe43d2c` (`resume:…:7` and `resume:…:9`) waited in the queue behind a long QA job. The
resume route had already flipped the project to `in_progress`; nothing heartbeats a project whose job has not started,
so the stale-run reaper (in the worker since AE-0522) counted it stale and reaped it back to `awaiting_human` at
00:32:44 UTC while the run was still queued. The job ran later anyway, but the reap bumped `lock_version` (8 → 10) and
Pedro's open tab went stale (version conflict on the next action).

## Scope

- `CarouselRunReaperRepository.tick` skips every `in_progress` project that has a `generation_runs` row in `queued`,
  `retry_wait` or `running` (claimed): no stale observation, no reap, no overdue alert. The queue owns those projects:
  a queued resume has no driver yet, and a job whose driver died is recovered by its own re-pick (AE-0522 orphan
  recovery), which reaps and re-drives it.
- `generation_queue.public.projects_with_active_runs(session, project_ids)`: the facade query the reaper uses.
- The autopilot `run_stale` escalation needs no change: an autopilot run's gate is only evaluated by its own job,
  which holds the drive lock and writes the heartbeat.

## Non-Goals

- Heartbeating queued runs or changing the resume route's `in_progress` flip.
- Changing the reaper's thresholds.

## Acceptance Criteria

- [x] AC1 Given a project left `in_progress` by a dashboard resume queued behind a long job, with a stale heartbeat,
  When the reaper ticks more than its reap threshold, Then the project stays `in_progress` and its `lock_version` is
  unchanged; the same holds while the run is `running` (`test_resume_queued_behind_a_long_job_is_not_reaped`).
- [x] AC2 Given that run then finishes, When the project is still stale, Then the reaper reaps it after its usual
  observations (same test).
- [x] AC3 The test fails on the old reaper (seeded: 1 failed with `origin/main`'s reaper).

## Repro Steps

1. Queue a long job (concurrency 1), then approve a gate on another carousel from the dashboard.
2. Wait past `heartbeat_stale_seconds` × the reap observations while the second job is still queued.
3. Before: the second project goes back to `awaiting_human` with `lock_version` + 2. After: it stays `in_progress`
   until its job runs.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0522 (#275, merged).

## Progress Log

### 2026-10-25 00:50

Ticket created from the AE-0522 prod validation finding; fix and test written.

## Files Touched

- `backend/src/rag_backend/infrastructure/database/carousel_run_reaper.py`
- `backend/src/rag_backend/modules/generation_queue/public.py`
- `backend/tests/unit/infrastructure/test_carousel_run_reaper.py`
- `backend/tests/features/carousel_run_progress_reaper.feature`

## Test Evidence

See `.agent/reports/AE-0548.dev-summary.md`.

## QA Report

Pending.

## Blockers

None.
