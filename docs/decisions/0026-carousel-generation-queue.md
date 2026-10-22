---
status: proposed
date: 2026-10-22
decision-makers: Pedro Marins
consulted: architecture review (AE-0517)
informed: delivery team
---

# ADR-0026: Run carousel generation through a Postgres-backed job queue in a separate, resource-capped worker

## Context and Problem Statement

The Grok Bot delivers 1-3 topics every morning (08:00 São Paulo). Each becomes an `autopilot_runs` row, and
Pedro receives one POV-thesis prompt per run on Telegram at the same time. Today generation has no queue:

- The only scheduler is a 60 s loop inside the single uvicorn process (`application/workers/workflow_workers.py`).
  It steps at most one autopilot run per tick and awaits each LLM phase inline, so one phase blocks the
  reapers, Instagram publish and Telegram notices for minutes. One-at-a-time is an accident of `RUNS_PER_TICK=1`.
- Interactive resumes are fire-and-forget `asyncio.create_task`s with no global limit.
- All generation shares the website's event loop. CPU work (PIL re-saves, img2pdf) blocks web requests, and every
  export launches headless Chromium four times (PT/EN × standard/HD).
- A deploy is a hard stop (`docker compose down`, 10 s grace). In-flight runs are lost; the reaper parks them for a
  human; nothing re-runs them automatically. Topics over the daily cap are stored and never queued.
- The droplet is a 2 vCPU / 3.8 GB box with ~860 MB available and ~190 % committed memory. The backend container
  has no memory limit, so an export spike can push the kernel OOM killer onto the web tier.

How do we let Pedro approve several themes, process them one after another (or with a small bounded
concurrency), retry transient failures, park poison runs in a dead-letter state, recover stuck runs daily, and
keep the website fast, without new paid services or heavy infrastructure?

## Decision Drivers

- Free and light: no new service, no new subscription; reuse Postgres, which already holds the run state.
- Protect visitors: generation must never share the web event loop or be able to OOM the web tier.
- Durable across deploys and crashes; at-least-once execution with idempotent steps (LangGraph checkpointer).
- Visible: Pedro sees the queue, positions, failures and can retry from the dashboard and Telegram.
- Fits the existing autopilot state machine (CAS transitions + outbox events) and `run_epoch` fencing.
- Prod applies schema with `create_all` (new tables yes, new columns no); prefer new tables over new columns.

## Considered Options

1. **In-house Postgres job table (`generation_jobs`) + `FOR UPDATE SKIP LOCKED` claim + lease/heartbeat, consumed by a
   separate worker container** (same image, different command).
2. **PgQueuer** (MIT, asyncpg-native Postgres queue with retries, held failures, heartbeats and cron) in the same
   separate worker container.
3. **Procrastinate** (MIT Postgres queue; async driver is psycopg3, a second Postgres driver next to asyncpg).
4. **Redis-based queue** (arq — maintenance-only since 2025; Redis Streams consumer groups; Taskiq/Dramatiq).
5. **Celery** (+ beat).
6. **LangGraph Agent Server** self-hosted (built-in task queue).
7. **Keep the in-process loop** and only add limits (semaphores, stagger).

## Decision Outcome

Chosen option: **1, an in-house `generation_jobs` table consumed by a separate `generation-worker` container**,
because it reuses the existing CAS/outbox/fencing patterns and the autopilot state machine, deploys with
`create_all` (one new table, no new columns), adds no dependency, and keeps the queue semantics (lease, attempts,
backoff, dead letter) in ~300 lines we test like any domain code. Option 2 (PgQueuer) is the fallback if the
in-house lease/retry code proves fragile: its tables would need a deploy one-shot (`pgq upgrade`) and its
stale-heartbeat attempt accounting is undocumented, which is why it is not the first choice.

Rejected: 3 adds a second Postgres driver; 4 makes Redis a second source of truth (RDB/AOF loss windows, arq in
maintenance); 5 is heavy and has no native async tasks; 6 needs a paid LangSmith license; 7 keeps generation on
the web event loop and loses runs on every deploy.

### Consequences

- Good: the website no longer shares an event loop or memory budget with generation; deploys of the web
  backend no longer kill runs; transient failures retry with backoff; poison runs stop in `dead_letter` with the
  reason; a daily scan re-queues stuck work; Pedro sees and controls the queue.
- Good: concurrency becomes a setting (`GENERATION_WORKER_CONCURRENCY`, default 1) plus a global export
  semaphore of 1, so throughput can rise later without code changes.
- Bad: one more container (~150-300 MB RSS idle, capped) and ~300 lines of queue code we own.
- Bad: at-least-once semantics: every graph node and external call must be idempotent (keyed by run id + step);
  the LangGraph Postgres checkpointer already gives node-level resume.
- Neutral: Redis stays for what it does today; the in-process loop keeps only light periodic steps.

## Validation

- Load test on a staging-like box: 3 queued runs while a k6/hey script measures web p95 latency; p95 must stay
  within 20 % of the idle baseline and no container may be OOM-killed.
- Chaos: kill the worker mid-phase and redeploy the backend mid-run; the job must resume (lease expiry) without
  duplicate artifacts or duplicate Telegram messages.

## More Information

Architecture plan: `.agent/reports/AE-0517.arch-plan.md`. Related: ADR-0020 (Grok Bot autopilot), ADR-0022 (image
bridge), AE-0017 recovery plan (asks for an ADR before any new queue mechanism), AE-0339, AE-0342, AE-0410, AE-0495.
