# AE-0517 — Carousel generation queue, dead letter and daily recovery

Status: Intake
Tier: T3
Priority: High
Type: Feature
Area: Backend
Owner: Architect
Agent Lane: architect → planner → developer → qa → release
Branch: docs/ae-0517-carousel-queue-plan
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Pedro can approve several carousel themes on the same day and they are generated one after another (bounded
concurrency) without blocking each other, without slowing the website for visitors, and without being lost on
deploys or crashes. Transient failures retry automatically, runs that keep failing land in a visible dead-letter
state with the reason, and a daily scan recovers stuck work. No new paid service and no heavy infrastructure.

## Problem

- Every morning the Grok Bot delivers 1-3 topics and Pedro receives all POV-thesis prompts on Telegram at once.
- There is no queue: one 60 s loop inside the single uvicorn process steps one autopilot run per tick and awaits
  each LLM phase inline; interactive resumes are unbounded `asyncio.create_task`s in the web process.
- Generation shares the website's event loop and memory: 4 headless Chromium launches per carousel and synchronous
  PIL/img2pdf work on a 2 vCPU / 3.8 GB droplet with ~860 MB available.
- Deploys stop the backend with no grace period; in-flight runs are parked for a human and never re-run; topics over
  the daily cap are never queued; some carousels stay stuck (10-21 and 10-22 each had a `run_stale` escalation).

## Plan

Architecture plan: `.agent/reports/AE-0517.arch-plan.md`. Decision: `docs/decisions/0026-carousel-generation-queue.md`
(proposed): Postgres `generation_jobs` table (SKIP LOCKED claim, lease + heartbeat, attempts, backoff with jitter,
dead letter) consumed by a separate `generation-worker` container (same image) with cgroup CPU/memory limits and a
global export lock. Phased P0-P5 (see plan §5); each phase is its own ticket and PR.

## Acceptance Criteria

- AC1 Given three themes confirmed within one minute, When the queue processes them, Then at most
  `GENERATION_WORKER_CONCURRENCY` (default 1) generate at the same time and the others wait in FIFO order with a
  visible position.
- AC2 Given a carousel is exporting slides, When a visitor loads the website, Then web p95 latency stays within 20 %
  of the idle baseline and no container is OOM-killed (load test on a staging-like box).
- AC3 Given the worker or the backend restarts during a phase, When the lease expires, Then the job is claimed again
  and resumes from the LangGraph checkpoint without duplicate artifacts or duplicate Telegram messages.
- AC4 Given a transient provider error, When the job fails, Then it retries with exponential backoff and jitter up to
  `max_attempts`; Given a permanent error or attempts exhausted, Then it moves to `dead_letter` with a classified reason.
- AC5 Given a job in `dead_letter`, When Pedro taps "Tentar de novo" on Telegram or Retry in the dashboard, Then it is
  re-enqueued once (CAS), and "Descartar" cancels it.
- AC6 Given the daily recovery scan runs (04:00 BRT, once per day), When it finds approved runs without an active job
  or stuck in-progress projects without a live lease, Then it re-enqueues them and sends Pedro one summary message.
- AC7 Given the same confirmation arrives twice (double tap or webhook retry), When it is processed, Then exactly one
  job exists (dedupe key).
- AC8 Given `GENERATION_QUEUE_ENABLED=false`, When the system runs, Then the current in-process path is unchanged
  (rollback by flag; new table only, no schema rollback).

## Pedro's decisions (2026-10-22)

- Concurrency: 1 carousel generating at a time (`GENERATION_WORKER_CONCURRENCY=1`).
- Over-cap themes roll to the next day's slot AND are listed in the dashboard where Pedro can trigger any of them
  manually (enqueue now, outside the daily cap).
- Daily recovery scan at 04:00 BRT.
- Strict FIFO: dashboard-started runs do not jump ahead of queued autopilot runs.

## Decision Log

- 2026-10-22: ADR required (new queue mechanism; AE-0017 recovery plan requires an ADR first). Chosen in-house
  Postgres job table + separate capped worker over PgQueuer (fallback), Procrastinate, Redis/arq, Celery, LangGraph
  Agent Server (paid license) and keeping the in-process loop. Evidence: capacity profile and run-model map in the
  plan §2.
- 2026-10-22: Pedro decided concurrency 1, over-cap roll-over + manual trigger from the dashboard, scan 04:00 BRT,
  strict FIFO (no priority ordering).
