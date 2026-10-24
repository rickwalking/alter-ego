# AE-0522 — P1 — PgQueuer queue, generation_runs, dispatcher and capped worker (live on merge)

Status: Ready
Tier: T3
Priority: High
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Move all carousel generation out of the web process into a resource-capped PgQueuer worker that is live as soon as this ticket merges (no feature flag, Pedro), per ADR-0026 and the AE-0517 plan §4.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the
disposable droplet → AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Pinned PgQueuer + deploy one-shot (`pgq install/upgrade`, `generation_runs` DDL generated from the Alembic migration, CI equality test).
- `generation_runs` table, transactional-outbox enqueue from approvals/resume, dispatcher (enqueue + dead-letter reconciler, 10 s), entrypoints with retry executor, per-(run, phase) attempt budgets, OOM non-retryable.
- Worker compose service: same image, `pgq run …`, concurrency 1, memory cap 1536M (prod run peak 1181 MiB + 30 %, from AE-0521/AE-0542) and, in the same change, the backend cap lowered from 1536M to 512M (web-only peak + 30 %; Pedro), CPU caps, hardening baseline, `--no-sandbox` Chromium with compensating controls, dedicated lock connection, checkpointer must be postgres.
- Single ownership lock (per-project advisory lock); existing autopilot run statuses keep their meaning so a revert strands no queued run, and the worker keeps writing the carousel heartbeat/phase columns so the reverted stale-run reaper still parks its in-flight run; NOTIFY progress relay with state-on-reconnect; queue metrics + alerts; pre-down drain step in deploy.yml.
- Gates before merge: PgQueuer semantics matrix (a)-(h) against the pinned source; side-effect inventory all outboxed or CAS-claimed; AE-0520 run_stale root cause known; export green under the exact hardened config.

## Non-Goals

- Telegram UX (AE-0523), daily scan (AE-0524), dashboard panel (AE-0526), checkpoint pruning (AE-0525). No feature flag and no flag-off path.

## Acceptance Criteria

- [ ] AC1-AC8 of AE-0517 (queue order, visitor latency, resume after deploy/crash, retries/dead letter, retry from Telegram/dashboard, daily scan hook, dedupe, rollback by revert).
- [ ] AC9 Given two claimants (two worker processes, or the worker and any web path that still drives a phase) claim the same project concurrently, Then exactly one drives (deterministic race test).
- [ ] AC10 Given PgQueuer holds a job after exhausting retries, When the dispatcher runs, Then `generation_runs` shows `dead_letter` and one Telegram notice is staged within 1 minute.
- [ ] AC12 Given the worker goes live on merge, Before the merge a disposable droplet of the production size passes: a load
  test with 3 queued runs where web p95 stays within 20 % of the idle baseline and no container is OOM-killed; the worker
  killed mid-phase; a full deploy mid-run (each run resumes within 6 min); one revert of the merge that strands no queued
  run; and no duplicate artifact or duplicate Telegram message in any of them.
- [ ] AC11 Given the validation droplet is built, Then it contains no production outbound credential (hash check) and cannot reach Telegram/Meta/Pinecone/Grok/LLM endpoints.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-23 (Pedro): no feature flag. The worker is live on merge, the disposable-droplet validation runs before the
  merge, and rollback = revert.
