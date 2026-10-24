# AE-0522 — P1 — PgQueuer queue, generation_runs, dispatcher and capped worker (live on merge)

Status: In Development
Tier: T3
Priority: High
Type: Feature
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: feat/ae-0522-pgqueuer-worker
Kanban Card: TBD
Created: 2026-10-22
Updated: 2026-10-23

## Goal

Move carousel generation out of the web process into a resource-capped PgQueuer worker, per ADR-0026 and the AE-0517
plan §4. The worker goes live when this PR merges (Pedro, 2026-10-23: no feature flag); the disposable-droplet
validation runs against this branch before the merge.

## Problem

Phase of AE-0517 (carousel generation queue). Plan: `.agent/reports/AE-0517.arch-plan.md`; decision:
`docs/decisions/0026-carousel-generation-queue.md` (provisional until the AE-0520 exit criteria hold); skeptical review:
`.agent/reports/AE-0517.skeptical-review.md`. Order: AE-0520 → AE-0521 → validation on the droplet →
AE-0522 (live on merge) → AE-0523, AE-0524, AE-0525, AE-0526.

Today every autopilot phase runs inline in the uvicorn process's 60 s loop, interactive resumes are unbounded
`asyncio.create_task`s on the web event loop, and a deploy kills a running phase: the AE-0520 root cause of the 10-21
and 10-22 `run_stale` escalations.

## Scope

- Pinned PgQueuer (`pgqueuer[asyncpg]==1.6.0`) and an idempotent deploy one-shot
  (`python -m rag_backend.scripts.generation_queue_schema --apply --verify`): `generation_runs` DDL compiled from the
  ORM table the Alembic migration creates (CI equality test), its indexes, and `install`/`upgrade` of PgQueuer's tables.
- `generation_runs` (source of truth for Telegram, the dashboard and idempotency): Alembic migration + the one-shot.
- Transactional outbox: every move of an autopilot run into `queued`, `generating` or `reworking` (intake, thesis
  confirmation, owner rework, runner moves) and every dashboard resume stages a `generation_runs` row in the same
  transaction (`ON CONFLICT DO NOTHING` on the active dedupe key). Approvals never touch PgQueuer's tables.
- Dispatcher in the worker, every 10 s: stages a row for any active autopilot run that has none (safety net), hands
  undispatched rows to PgQueuer (looking the job up by dedupe key first), and mirrors held (failed) PgQueuer jobs into
  `dead_letter` with one Telegram notice staged through the outbox.
- One PgQueuer entrypoint (`carousel_generation`, `concurrency_limit = GENERATION_WORKER_CONCURRENCY`, default 1,
  `on_failure="hold"`), strict FIFO across kinds: `autopilot_drive` (steps one autopilot run until it waits for the
  owner or ends) and `workflow_resume` (the dashboard approve/revise/redrive).
- Attempt budgets in `generation_runs`: at most 3 unfinished attempts per (run, phase) and 10 per run; a run that
  keeps advancing is never dead-lettered. Transient errors retry with exponential backoff and ±20 % jitter (30 s,
  ×2, max 30 min); permanent errors (validation, missing project, `MemoryError`) dead-letter at once.
- Ownership: the per-project drive lock (session advisory lock on a dedicated connection, held for the whole drive)
  is the only ownership primitive; the worker takes it for every job, the synchronous dashboard start takes it too.
  Losing the lock connection aborts the drive. A job that gets the lock and finds the project `in_progress` from its
  own interrupted attempt reaps it at once and re-drives the parked node (resume after deploy/crash).
- Worker: `rag_backend.worker.main:create_pgqueuer` (same image, `pgq run`), `heartbeat_timeout` 300 s, CPU-heavy
  steps already off the event loop (AE-0520), refuses to start unless the checkpointer is `postgres`. The heavy
  periodic steps (autopilot runner, stale-run reaper, drift reconciler, republish sweeper) move from the web loop to
  the worker; the web keeps the light steps (scheduled publish, reminders, alerts, Telegram notices, Instagram
  publish, credential refresh, blog reaper, auto-archive).
- Compose service `generation-worker`: same image, capped (`mem_limit` = `memswap_limit` = 1600M, the prod run peak
  1222 MiB + 30 %; the backend keeps 1600M because it still renders the dashboard exports, finalize and refinement,
  and the cross-process export slot keeps one Chromium export on the box at a time; budget in
  `.agent/reports/AE-0522.memory-budget.md`; `cpus`, `cpu_shares` 256, `shm_size`), `cap_drop: ALL`, `no-new-privileges`, read-only root with tmpfs, no published ports, own healthcheck,
  `stop_grace_period` 300 s; Chromium runs with Playwright's default `--no-sandbox` under those compensating controls.
- Deploy: the one-shot after the archived_at step, and a drain before `down -t 120` (`docker compose stop -t 300
  generation-worker`: the worker stops dequeuing, finishes or checkpoints the current phase). The one-shot also
  queues a recovery for each project left `in_progress` with no active run and no autopilot run (the cutover).
- Progress relay: the worker's SSE events go through Postgres `NOTIFY carousel_progress`; the web listens and feeds
  its in-process hub; an SSE (re)connect still starts from the current state.
- Queue metrics on `/health/ready` (depth, oldest queued age, running age, dead letters, worker last seen) and an alert
  through the alerts bot when the worker has not been seen for 10 min or the oldest queued run waits over 6 h.
- Disposable-droplet validation as a reproducible script (`ops/queue-validation/`): provision, deploy the branch with
  stubbed credentials, egress firewall, credential-hash check, load test, chaos steps, teardown.

## Non-Goals

- Telegram UX (AE-0523: queue position, "Aprovar todas", dead-letter buttons), daily scan (AE-0524), dashboard
  panel and retry/cancel API (AE-0526), checkpoint pruning (AE-0525).
- Moving the synchronous dashboard start into the worker (pending Pedro's answer; it takes the drive lock here).
- Holding a DigitalOcean token in the repo: the validation script reads a token file outside the repo
  (Pedro approved the droplet on 2026-10-23; the token is requested separately).

## Acceptance Criteria

- [x] AC1 Given three autopilot runs queued within one minute, When the worker processes them, Then at most
  `GENERATION_WORKER_CONCURRENCY` (default 1) generate at a time and the others wait in FIFO order (AE-0517 AC1).
- [ ] AC2 Given a carousel exporting slides on the droplet, When the load script hits the site, Then web p95 stays
  within 20 % of the idle baseline and no container is OOM-killed (AE-0517 AC2; droplet validation).
- [x] AC3 Given the worker is killed or the stack is redeployed mid-phase, When the worker comes back, Then the job is
  picked again, the interrupted node re-runs from the checkpoint and the run continues without escalating `run_stale`,
  with no duplicate artifacts or Telegram messages (AE-0517 AC3).
- [x] AC4 Given a transient error, Then the job retries with exponential backoff and jitter; Given a permanent error or
  an exhausted (run, phase) budget, Then `generation_runs` shows `dead_letter` with a classified reason (AE-0517 AC4).
- [x] AC5 Given a dead-lettered run, When it is requeued (CAS on `dead_letter`, attempts of the failing phase reset),
  Then it runs once more (the API/Telegram buttons are AE-0523/AE-0526; this ticket ships the repository operation).
- [x] AC6 Given an active autopilot run with no active generation row (rows from before the deploy, a missed stage),
  When the dispatcher runs, Then it stages and dispatches one (the hook the daily scan of AE-0524 reuses).
- [x] AC7 Given the same confirmation or resume twice, Then exactly one active generation row and one PgQueuer job
  exist (dedupe key).
- [x] AC8 Given the PR is reverted, Then the in-process runner drives runs again from `autopilot_runs`, no run is
  stranded and no schema rollback is needed.
- [x] AC9 Given two drivers claim the same project concurrently, Then exactly one drives (deterministic race test).
- [x] AC10 Given PgQueuer holds a job after a failure the handler did not mirror, When the dispatcher runs, Then
  `generation_runs` shows `dead_letter` and one Telegram notice is staged within 1 minute.
- [x] AC11 Given the validation droplet is built, Then it holds no production outbound credential (hash check) and
  cannot reach Telegram/Meta/Pinecone/Grok/LLM endpoints.
- [x] AC12 Given the deploy one-shot runs twice, Then `generation_runs`, its indexes and PgQueuer's tables exist once
  and the second run is a no-op; `--verify` fails when any is missing; the DDL equals the Alembic migration's.
- [x] AC13 PgQueuer semantics gate against the pinned 1.6.0 source, each an integration test: (a) a held job does not
  block a new job with the same dedupe key and a requeue with the same key is accepted, (b) delayed enqueue,
  (c) configurable heartbeat timeout re-picks a stale job, (d) a stale re-pick does not count an attempt (our own
  counter does), (e) FIFO under `concurrency_limit=1`, (f) held-job requeue, (g) schedule dedupe across workers,
  (h) retention: log rows can be purged by age.
- [ ] AC14 Given the pre-merge disposable-droplet validation (load test with 3 queued runs, web p95 within 20 % of the
  idle baseline and no OOM kill; the worker killed mid-phase; a full deploy mid-run, each run resuming within 6 min;
  one revert of the merge that strands no queued run; no duplicate artifact or Telegram message in any of them), Then
  its results are attached to the PR before merge (Pedro approved the droplet on 2026-10-23).
- [x] AC16 Given a carousel project left `in_progress` with no active run and no autopilot run (a dashboard resume the
  cutover deploy stopped), When the deploy one-shot runs, Then one recovery is queued for it (none for a project whose
  drive lock is held or that belongs to an autopilot run, none on a second run), and the worker reaps it and re-runs the
  parked node without a review decision (`test_generation_cutover_ae0522.py`, `test_generation_recovery_ae0522.py`).
- [x] AC15 Given a revert, Then no queued run is stranded: existing autopilot run statuses keep their meaning (a run
  waits as `queued` on `autopilot_runs`, never only as a `generation_runs` row) and the worker keeps writing the
  carousel heartbeat and phase columns, so the reverted stale-run reaper parks an in-flight run.

## Gherkin Scenarios

- `backend/tests/features/generation_queue_ae0522.feature`

## Affected Areas

- Backend: new `modules/generation_queue` (domain, application, infrastructure, public facade), `worker/` entry,
  autopilot repository stage hooks, resume route, workflow workers split, app factory, settings, one-shot script,
  Alembic migration, `/health/ready` metrics.
- Database: new table `generation_runs` (+ PgQueuer's own tables), Alembic + deploy one-shot.
- Deployment: `docker-compose.prod.yml` worker service, `deploy.yml` one-shot + drain.
- Ops: `ops/queue-validation/` droplet validation script.
- Docs: ADR-0026 validation (no flag), AE-0517 plan §7, tickets AE-0517/0520..0526 order line.

## Dependencies

- Blocked by: AE-0521 (web-tier memory caps) must merge before this PR; built in parallel and rebased.
- Related: AE-0520 (P0, merged), AE-0523..AE-0526.

## Progress Log

### 2026-10-23

Pedro decided there is no feature flag: removed the flag from ADR-0026, the AE-0517 plan, AE-0517 AC8 and this ticket;
added AC14 for the pre-merge droplet validation. Worktree `feat/ae-0522-pgqueuer-worker` off origin/main.

Built the queue (module `modules/generation_queue`, worker `rag_backend/worker`), the PgQueuer semantics gate (all
eight properties hold on 1.6.0; PgQueuer has no age-based purge, so AE-0524 deletes old `pgqueuer_log` rows itself),
the deploy one-shot, the compose service and the drain, the rollback one-shot and the validation tooling.

Local rehearsal of the validation scenario (Postgres, web, worker, mock upstream, real Chromium export): nine themes
went research → export → `awaiting_owner` with one ready notice each; a worker killed with SIGKILL mid-outline was
re-picked, reaped and re-driven to completion (one notice, one active build); SIGTERM stopped the drive at the next
phase boundary and the job resumed on restart.

## Files Touched

- Queue module: `backend/src/rag_backend/modules/generation_queue/**` (constants, domain models/budget/errors/ports/
  health, application handler/executors/dispatcher/monitor, infrastructure store/staging/PgQueuer gateway/drive lock/
  adapters/notices/relay/metrics/schema/rollback, bootstrap, public facade).
- Worker: `backend/src/rag_backend/worker/{main,periodic,healthcheck}.py`.
- Autopilot: `application/runner.py` (`step`, `sweep`, `park`, retryable errors), `application/runner_deps.py`,
  `application/run_recovery.py` (`park`), `application/run_spec.py` + `domain/gate.py` + `infrastructure/editorial_driver.py`
  (deterministic carousel id per run), `queue_bridge.py`, `bootstrap.py`, `constants.py`.
- Image bridge: `application/grokbot_image_service.py` (a re-run image waits on its pending job), `constants.py`.
- Web: `bootstrap/app_factory.py` (heavy steps removed from the web loop, relay + monitor, readiness numbers),
  `bootstrap/generation_queue_web.py`, `bootstrap/observability.py`, `bootstrap/autopilot_worker_factory.py`,
  `bootstrap/carousel_run_reaper_factory.py`, `api/routes/carousels/editorial_workflow.py` (resume queues; start holds
  the drive lock), `application/services/carousel/workflow_sse_hub.py`, `infrastructure/database/{config,carousel_run_reaper}.py`,
  `infrastructure/config/{settings,generation_queue_settings}.py`, `infrastructure/notifications/llm_alerts.py`.
- Schema: `alembic/versions/d1b0cf9cd80d_generation_runs.py`, `scripts/generation_queue_{schema,rollback}.py`,
  `scripts/cli_support.py`; `docker-compose.prod.yml`, `docker-compose.yml`, `.github/workflows/deploy.yml`,
  `backend/.importlinter`, `backend/pyproject.toml`, `uv.lock`, `docs/architecture/openapi.json`.
- Validation: `ops/queue-validation/*`.
- Tests: `backend/tests/features/generation_queue_ae0522.feature` and the tests that name its scenarios; resume
  integration tests now run the queued work through the real job handler (`tests/integration/generation_queue_support.py`).

## Test Evidence

See `.agent/reports/AE-0522.dev-summary.md`.

## QA Report

See `.agent/reports/AE-0522.qa.md`.

## Decision Log

- 2026-10-22: Created from the AE-0517 plan after three skeptical review rounds (Pedro's cap).
- 2026-10-23: Pedro decided there is no feature flag: the worker goes live on merge, the disposable-droplet validation
  (load test, worker killed mid-phase, deploy mid-run, no duplicate artifacts or Telegram messages) runs before the
  merge, rollback is a revert. The flag hand-overs are dropped; `GENERATION_WORKER_CONCURRENCY=1` and the single
  ownership lock stay.
- 2026-10-23: One PgQueuer entrypoint for every job kind, so `concurrency_limit` is global and FIFO holds across kinds
  (PgQueuer's limit is per entrypoint). One `autopilot_drive` job steps a run until it waits for the owner, so themes
  are generated one after another instead of interleaving phase by phase.
- 2026-10-23: The outbox of an autopilot approval is the autopilot run's own compare-and-set (its state row is durable
  and transactional): the dispatcher stages a generation run for every queued/generating/reworking autopilot run within
  10 s, so no autopilot write path touches the queue. A dashboard resume has no other durable record of its review
  decision, so the route stages its generation run in the same transaction as the lock bump.
- 2026-10-23: A job that gets the drive lock and finds its project `in_progress` reaps it at once and re-drives the
  parked node (the lock proves the previous driver is gone), unless another queued dashboard resume owns that phase.
  A re-picked dashboard resume never re-sends the review decision.
- 2026-10-23: Transient engine errors in an autopilot step (provider outage, rate limit, timeout) are raised to the queue
  for backoff retries; any other engine error is still contained by the runner (escalated). Dead-lettering an autopilot
  run parks it as an engine error does (`escalated`, reason `queue_dead_letter:<code>`), which sends the one owner notice.
- 2026-10-23: Side-effect merge gate (AE-0520 inventory): a re-delivered start reuses the run's carousel (id derived
  from the run); a re-run image waits on the Grok Bot job still pending for the same image and prompt; revise feedback
  and corrections are never re-applied (re-picks re-drive, they do not resume). Telegram dispatch stays in the web.
- 2026-10-23: The worker keeps `TELEGRAM_BOT_TOKEN`/`TELEGRAM_OWNER_CHAT_ID` in its environment only because the runner
  escalates a run as `notifier_unconfigured` without them; it sends nothing (the web delivers the outbox).
- 2026-10-23: Validation uses synthetic data (seeded owner, persona and Radar IA runs), not a production backup, so no
  production data reaches the droplet. The worker container is capped at 1600 MiB (prod HD run peak 1222 MiB + 30 %).
- 2026-10-23: The drive lock uses its own key space, not the artifact-mutation lock: the runner's own autofix and
  slide-fix steps take the mutation lock from inside a drive, and advisory locks are not re-entrant across sessions.

## Blockers

None.

## Final Summary

Pending.
- 2026-10-24: Review fixes on #275: the staging clock is injected (the date-dependent test), the worker cap is 1536M
  (prod run peak 1181 MiB + 30 %) and the backend keeps 1536M for its in-process renders (Langfuse is off the box,
  budget in `.agent/reports/AE-0522.memory-budget.md`), decision ids out of code, ADR-0026 and plan §4.3 describe the
  dispatcher-staged autopilot path, the cutover adoption in the deploy one-shot (AC16), FIFO gaps documented (plan §9),
  `down -t 120`. Rebased onto #270 (alembic `d1b0cf9cd80d` now on `344dec4495d3`) and #279. Pedro is skipping the
  droplet validation for now (no DigitalOcean token): AC2 and AC14 stay open.
- 2026-10-24: Last round: the latest measured run peak is 1222 MiB, so the worker AND the backend are capped at 1600M
  (the backend keeps the Chromium renders); budget redone on today's prod (2264 MiB available, no Langfuse or MinIO).
  Pedro approved merging without the disposable-droplet validation (rollback = revert) and asked for a prod-safe
  validation with one QA carousel instead (`validate.sh --target prod`), run only when he says go.
