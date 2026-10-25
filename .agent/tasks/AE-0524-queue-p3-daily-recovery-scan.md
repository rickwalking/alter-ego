# AE-0524 — P3 — daily recovery scan and summary

Status: In Development
Tier: T2
Priority: Medium
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0524-daily-recovery-scan
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-24

## Goal

A once-a-day scan at 04:00 BRT (PgQueuer schedule) that re-queues stuck or idle work and sends Pedro one summary, per the AE-0517 plan §4.6.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- PgQueuer schedule `0 7 * * *` (UTC = 04:00 São Paulo) in the generation worker; PgQueuer's schedule table makes it
  run once a day across workers and restarts (semantics verified in AE-0522).
- Retry once each autopilot drive the queue dead-lettered in the last 7 days with a transient-class code
  (`transient`, `phase_budget_exhausted`, `run_budget_exhausted`, `held_by_queue`): the row is marked
  `recovery_attempt` first (compare-and-set), then the autopilot run is revived through the queue bridge (the same
  revive as the Telegram "Tentar de novo": escalated → generating with the dead letter requeued in one transaction;
  failed → a new run). A run Pedro already resolved is not touched. Dashboard dead letters are left to the editor's
  Retry.
- Resume autopilot runs escalated as `run_stale` in the last 72 hours (escalated → generating; the dispatcher stages
  the drive, which re-drives from the checkpoint).
- List dashboard projects left in progress with nothing queued (they stay parked).
- Purge succeeded generation runs and PgQueuer log rows older than 30 days.
- One summary to Pedro through the alerts bot: recovered, still dead, queued, parked dashboard projects.
- Already in AE-0522 and not repeated here: staging autopilot runs without an active job (dispatcher, every 10 s),
  adopting orphaned dashboard resumes at deploy, `/health` `worker_last_seen` + alert.

## Non-Goals

- Checkpoint pruning (AE-0525).

## Acceptance Criteria

- [ ] AC1 Given the scan runs twice on the same day (two workers or a restart), Then it acts once: PgQueuer fires the
  schedule once, and a dead letter already tried is never retried again.
- [ ] AC2 Given a stuck autopilot run (a transient dead letter or a stale escalation), When the scan runs, Then it is
  re-queued and resumes from its checkpoint.
- [ ] AC3 Then Pedro receives one summary message with recovered, still-dead and queue counts (and the parked
  dashboard projects).

## Gherkin

`backend/tests/features/daily_recovery_scan_ae0524.feature`.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-24 (Pedro: no feature flags, strict FIFO, concurrency 1): the "one retry" marker is a payload key on the
  generation run (no schema change); the autopilot revive is shared with the Telegram retry (AE-0523), so the scan
  goes through the queue bridge. Dashboard projects are listed, not resumed (the plan's rule for interactive runs).
- 2026-10-24 (review): "once" holds per theme: the run the scan queues carries a `daily_recovery` ledger key, so a
  failed run's retry is never retried again and a stale run is resumed once (and not in its first hour, while the
  reaper may still be at it); each stale revive has its own transaction; tried dead letters no longer hide newer ones;
  "parados" counts the last 7 days; PgQueuer's log table name comes from PgQueuer's settings.
