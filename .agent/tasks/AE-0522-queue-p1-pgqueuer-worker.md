# AE-0522 — P1 — PgQueuer queue, generation_runs, dispatcher and capped worker (flag off)

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

Move all carousel generation out of the web process into a resource-capped PgQueuer worker behind GENERATION_QUEUE_ENABLED (default off), per ADR-0026 and the AE-0517 plan §4.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → AE-0522 (flag off) → validation → flag on →
AE-0523, AE-0524, AE-0525, AE-0526.

## Scope

- Pinned PgQueuer + deploy one-shot (`pgq install/upgrade`, `generation_runs` DDL generated from the Alembic migration, CI equality test).
- `generation_runs` table, transactional-outbox enqueue from approvals/resume, dispatcher (enqueue + dead-letter reconciler, 10 s), entrypoints with retry executor, per-(run, phase) attempt budgets, OOM non-retryable.
- Worker compose service: same image, `pgq run …`, concurrency 1, memory/CPU caps from AE-0521, hardening baseline, `--no-sandbox` Chromium with compensating controls, dedicated lock connection, checkpointer must be postgres.
- Single ownership lock on both paths; explicit flag hand-overs; NOTIFY progress relay with state-on-reconnect; queue metrics + alerts; pre-down drain step in deploy.yml.
- Gates before merge: PgQueuer semantics matrix (a)-(h) against the pinned source; side-effect inventory all outboxed or CAS-claimed; AE-0520 run_stale root cause known; export green under the exact hardened config.

## Non-Goals

- Telegram UX (AE-0523), daily scan (AE-0524), dashboard panel (AE-0526), checkpoint pruning (AE-0525). Enabling the flag in prod (separate step after validation).

## Acceptance Criteria

- [ ] AC1-AC8 of AE-0517 (queue order, visitor latency, resume after deploy/crash, retries/dead letter, retry from Telegram/dashboard, daily scan hook, dedupe, flag rollback).
- [ ] AC9 Given the web path and the worker claim the same project concurrently, Then exactly one drives (deterministic race test).
- [ ] AC10 Given PgQueuer holds a job after exhausting retries, When the dispatcher runs, Then `generation_runs` shows `dead_letter` and one Telegram notice is staged within 1 minute.
- [ ] AC11 Given the validation droplet is built, Then it contains no production outbound credential (hash check) and cannot reach Telegram/Meta/Pinecone/Grok/LLM endpoints.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
