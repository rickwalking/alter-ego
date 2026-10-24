---
status: proposed (accepted-provisional once P0 exit criteria 1-3 hold)
date: 2026-10-22
decision-makers: Pedro Marins
consulted: architecture review (AE-0517)
informed: delivery team
---

# ADR-0026: Run carousel generation through PgQueuer (Postgres job queue) in a separate, resource-capped worker

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

Chosen option (Pedro, 2026-10-22), **provisional until the P0 exit criteria hold** (measured run memory and HD decision,
a box memory budget that closes, root cause of the October `run_stale` escalations): **2, PgQueuer**, consumed by a separate `generation-worker` container (same image,
`pgq run …`), because it gives us a maintained, MIT-licensed, asyncpg-native queue with what we would otherwise build:
FIFO dequeue with `SKIP LOCKED`, a database-enforced concurrency limit, retries with exponential backoff, failed jobs
held aside (our dead letter), heartbeat-based requeue of jobs from dead workers, cron schedules for the daily recovery
scan, and a CLI to inspect and requeue jobs — so queue management is simpler to operate. It needs no new service
(Postgres is already there) and no new subscription.

Guards we add around it:

- PgQueuer installs its own tables (`pgq install` / `pgq upgrade`). Prod does not run migrations, so an idempotent
  deploy one-shot installs/upgrades them (palette_timestamptz pattern). The version is pinned.
- Approvals never call PgQueuer: they write our `generation_runs` row in their own transaction (transactional outbox);
  a dispatcher in the worker hands queued rows to PgQueuer. A broken PgQueuer install therefore cannot break approvals.
- A semantics gate (verified against the pinned source with integration tests) precedes merge; failures switch to the
  in-house fallback.
- Amends ADR-012 in practice: `generation_runs` ships as an Alembic migration plus the deploy one-shot, not via
  `create_all`.
- PgQueuer's docs do not say whether a stale-heartbeat requeue counts as an attempt, so our handler keeps its own attempt
  counter in `generation_runs` and dead-letters a run that exceeds it (poison/OOM-loop guard).
- Our `generation_runs` table stays the source of truth for the dashboard, Telegram, idempotency (dedupe key) and the
  autopilot state machine; PgQueuer job events are mirrored into it. The dashboard never reads PgQueuer's tables.
- `heartbeat_timeout` 300 s and CPU-heavy steps off the event loop (`asyncio.to_thread`), so heartbeats are never starved.

Not chosen: 1 (in-house table) — roughly the same surface minus PgQueuer's dequeue/heartbeat/requeue/schedule
primitives (our run table, outbox dispatcher and attempt counter exist either way); it stays the fallback if PgQueuer is ever abandoned, behind the same
entrypoints. 3 adds a second Postgres driver; 4 makes Redis a second source of truth (RDB/AOF loss windows, arq in
maintenance); 5 is heavy and has no native async tasks; 6 needs a paid LangSmith license; 7 keeps generation on the
web event loop and loses runs on every deploy.

### Consequences

- Good: the website no longer shares an event loop with generation and, once the web tier is capped (precondition),
  no longer competes for unbounded memory; runs interrupted by a deploy (the deploy restarts the whole project) or a
  crash resume automatically from the checkpoint after a drain step; transient failures retry with backoff; poison runs stop in a dead-letter state with the reason; a
  daily scan re-queues stuck work; Pedro sees and controls the queue; queue operations (list, requeue) come built in.
- Good: concurrency is a setting (`GENERATION_WORKER_CONCURRENCY`, Pedro: 1) plus a global export lock of 1.
- Bad: a third-party dependency with its own tables and a deploy one-shot to install/upgrade them; one more container
  (~150-300 MB RSS idle, capped).
- Bad: at-least-once semantics: every graph node and external call must be idempotent (keyed by run id + step); the
  LangGraph Postgres checkpointer already gives node-level resume.
- Neutral: Redis stays for what it does today; the in-process loop keeps only light periodic steps.

## Validation

- Preconditions for accepting this ADR (P0 exit criteria in the plan): measured carousel-run RSS and HD decision, a box
  memory budget that closes (possibly by shrinking the observability stack or a bigger droplet), the root cause of the
  October `run_stale` escalations, an inventory of node side effects with their idempotency, and an off-box p95 baseline.
- The test droplet never holds production outbound credentials (stubbed Telegram/Meta/Pinecone/Grok/LLM endpoints, egress
  firewall, credential-hash check); see the plan's "Validation isolation".
- Load test on a disposable droplet of the same size: 3 queued runs while a k6/hey script measures web p95 latency; p95 must stay
  within 20 % of the idle baseline and no container may be OOM-killed.
- Chaos: kill the worker mid-phase and run a full deploy mid-run; the job must resume within 6 min of the stack
  returning, without duplicate artifacts or duplicate Telegram messages.
- There is no feature flag (Pedro, 2026-10-23): the worker goes live when P1 merges, so the load and chaos validation
  above runs on the disposable droplet BEFORE the merge, and rollback is a revert of the merge (new tables only, no
  schema rollback).

## More Information

Architecture plan: `.agent/reports/AE-0517.arch-plan.md`. Related: ADR-0020 (Grok Bot autopilot), ADR-0022 (image
bridge), AE-0017 recovery plan (asks for an ADR before any new queue mechanism), AE-0339, AE-0342, AE-0410, AE-0495.
