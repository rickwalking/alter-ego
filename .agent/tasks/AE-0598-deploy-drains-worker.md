# AE-0598 — A deploy drains the generation worker and fits its timeout

Status: Dev Complete
Tier: T1
Priority: High
Type: Bugfix
Area: CI/CD, generation worker
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0598-deploy-drain-worker
Kanban Card: TBD
Created: 2026-11-02
Updated: 2026-11-02

## Goal

A deploy never kills an autopilot run it could have waited for, and the deploy job always reaches its post-start
checks. Pedro's decision (2026-11-02): drain plus a timeout margin.

## Problem

Deploy run 41529209741 (2026-11-02) timed out at the ssh-action's default `command_timeout` of 10 minutes. Every
container was up, but the post-start re-verify, the drift check and the health block never ran.

Before (measured from the run log):

| Step | Start → end (UTC) | Seconds |
|------|-------------------|---------|
| pull + build | 21:32:45 → 21:35:12 | 147 |
| `stop -t 300 generation-worker` (an autopilot run was in flight, it was killed and retried later) | 21:35:12 → 21:40:12 | 300 |
| `down -t 120` (opencode ignores SIGTERM) | 21:40:12 → 21:42:13 | 121 |
| postgres, nine one-shots, `up -d` | 21:42:13 → 21:42:43 | 30 |
| post-start checks | never ran | — |
| **total** | **timed out at 600 s** | 600 |

opencode used its full 120 s on every deploy, also on the green run 41453770433 (13:32:18 → 13:34:18).

Root causes:

1. The worker stop was the only way to stop a drive; a drive phase lasts minutes (prod, last 30 days, phase_succeeded
   durations: outline p50 975 s / p90 1481 s, research p50 294 s, design p50 251 s, images p50 51 s), so a stop in
   the middle of one always waited the full 300 s and then killed it.
2. opencode runs as PID 1 (`docker top`: one process, `opencode serve`, no init; `HostConfig.Init` unset). The
   entrypoint already `exec`s, so no shell is in the way: the kernel does not deliver a signal to PID 1 unless the
   process installed a handler for it, opencode does not, so SIGTERM was dropped and `down` waited for the SIGKILL.
3. 10 minutes left no margin for the post-start block once the two waits above ran in full.

## Scope

1. **Drain (behaviour change, Gherkin first).** The worker reads a drain flag (`/tmp/generation-worker.drain`, its own
   tmpfs) and keeps a busy marker (`/tmp/generation-worker.busy`) while a generation job is in the entrypoint.
   While the flag is fresh the entrypoint puts a picked job back to PgQueuer (`RetryRequested`, 30 s) before the
   handler sees it (the run is not claimed, no attempt is counted) and a drive yields at its next phase boundary
   (the same path as SIGTERM). `python -m rag_backend.worker.drain_cli drain|idle|clear` is the deploy's handle.
   The flag is ignored once older than 900 s (the ssh timeout) and removed when the worker starts.
2. **Deploy drain step.** `scripts/deploy/drain-generation-worker.sh drain <compose> 240 5` runs after the build:
   sets the flag, polls `idle` every 5 s for at most 240 s (wall clock), always exits 0. Then
   `stop -t 60 generation-worker` (240 + 60 = the old 300 s), then `down` as before. After `up -d`,
   `drain-generation-worker.sh clear` is a warn-only backstop.
3. **opencode.** `init: true` on the opencode service (Docker's tini is PID 1 and forwards SIGTERM).
4. **Timeout.** `command_timeout: 15m` on the deploy ssh step.

No check is removed or skipped: the pre-start one-shots, the post-start retries, the drift check, the health block,
the Redis probe and the secret-permission check all stay (pinned by `test_deploy_drains_worker_ae0598.py`).

### When the bounded wait runs out

The worker is stopped as before. The drive's phase is lost, not the run: its `generation_runs` row stays `running`
and its PgQueuer job stays `picked`; the new worker re-picks the job once its heartbeat is older than
`--heartbeat-timeout 300` (the dispatcher hands a vanished job over again too), the drive reaps the orphaned phase and
re-runs it from the last LangGraph checkpoint (scenario "A run interrupted by a deploy resumes by itself", AE-0522).
That is what happened to the run of 2026-11-02 and it stays the fallback.

### CI/config part: "unit tests suffice" record (AE-0153)

The deploy step, the compose `init` and the ssh timeout are CI/config; the worker drain carries the `.feature`.

- (a) No public or user-visible behaviour change from the deploy/compose parts: no API, UI or data change; the
  deploy runs the same checks in the same order, with a drain step before the worker stop.
- (b) Seeded-violation tests: `test_deploy_drains_worker_ae0598.py` runs each shape check on the real files AND on a
  seeded violation (the old deploy.yml without the drain and with `stop -t 300`; a dropped drift check; a dropped
  post-start retry; no `command_timeout`; compose without `init`), each must report the problem.
  `test_drain_generation_worker_ae0598.py` dry-runs the shell script against a stub `docker` that runs the real CLI.
- (c) Affected gates: none changed. `backend:test` / `backend:diff-cover` run the new tests.
- (d) Reviewer/QA sign-off on the no-`.feature` classification of the deploy/compose parts: pending (QA). The
  feature file covers them anyway (`deploy_drains_worker_ae0598.feature`).

## Non-Goals

- Making a phase interruptible mid-way (outline p50 is 16 min; no deploy waits that long).
- Changing the compose `stop_grace_period: 300s` of the worker (used outside the deploy).
- Draining maintenance jobs (scan, backlog promotion) or the periodic steps: they are short and commit per step.

## Acceptance Criteria

- [x] AC1 A drained worker does not claim a picked generation job; the job goes back to PgQueuer untouched and is
  claimed once the flag is cleared (unit + real PgQueuer on Postgres).
- [x] AC2 A drive in flight yields at its next phase boundary while drained; the busy marker is present exactly while
  a job is in the entrypoint (also when it raises, also with two in flight).
- [x] AC3 A flag older than 900 s is ignored; the worker removes the flag and the marker when it starts (unit + the
  real `create_pgqueuer` on Postgres).
- [x] AC4 The deploy drain step waits until idle, gives up after its bound with a warning, skips a stopped worker,
  never blocks the deploy (exit 0) and the clear step only warns; usage errors exit 2 without touching anything.
- [x] AC5 deploy.yml: build → drain → `stop -t 60` → down; clear after `up -d` and before the drift check; every
  check kept; `command_timeout: 15m`.
- [x] AC6 opencode stops on SIGTERM: `init: true`; measured locally 30.1 s (SIGKILL, exit 137) without init vs 0.13 s
  (exit 143) with it.
- [ ] AC7 The first deploy after merge finishes green under 15 minutes (measured after timing below).

## Gherkin Scenarios

- `backend/tests/features/deploy_drains_worker_ae0598.feature` (13 scenarios)
- `backend/tests/features/generation_queue_ae0522.feature`: the deploy scenario's last line now points at the drain.

## Timing

Expected after (from the measured steps above):

| Step | Idle worker | Busy past the bound (worst) |
|------|-------------|-----------------------------|
| pull + build | ~150 s | ~150 s (300 s on a cold build) |
| drain | ~3 s | ≤ ~250 s (240 s + one poll) |
| worker stop | ~3 s | ≤ 60 s |
| down (opencode now exits on SIGTERM; backend ~9 s) | ~10 s | ~10 s |
| postgres, one-shots, `up -d` | ~30 s | ~30 s |
| post-start (sleep 10, clear, drift, health, prune) | ~25 s | ≤ ~150 s (drift retries 12 × 10 s) |
| **total** | **~220 s** | **≤ ~650 s (~800 s cold build), under 900 s** |

Note: the first deploy of this change still runs the old worker image when it drains, which has no `drain_cli`: the
step warns "could not set the drain flag" and the deploy stops the worker without a drain (60 s grace). From the next
deploy on the drain is live.

Measured after (first deploy after merge): run ______, total ______ s, drain ______ s, worker stop ______ s,
down ______ s, result ______.

## Affected Areas

- Backend: `worker/drain.py`, `worker/drain_cli.py`, `worker/constants.py`, `worker/main.py`,
  `infrastructure/config/generation_queue_settings.py`
- Frontend: none
- Database: none
- API: none
- Tests: unit worker + scripts_ci, integration on Postgres
- Docs: this ticket
- Deployment: `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `scripts/deploy/drain-generation-worker.sh`

## Dependencies

- Related: AE-0522 (generation worker), AE-0207 (deploy order).

## QA Checklist

- [ ] Security reviewed (the CLI writes only two files in the worker's own tmpfs; no new secret, port or privilege)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-02

Studied the worker (PgQueuer entrypoint, `stopping` at phase boundaries, heartbeat re-pick), the incident and green
run logs, and the opencode container on prod (read-only). Wrote the feature, the worker drain, the deploy script, the
workflow and compose changes and their tests. Measured the opencode stop locally.

## Files Touched

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `scripts/deploy/drain-generation-worker.sh`
- `backend/src/rag_backend/worker/constants.py`, `drain.py`, `drain_cli.py`, `main.py`
- `backend/src/rag_backend/infrastructure/config/generation_queue_settings.py`
- `backend/tests/features/deploy_drains_worker_ae0598.feature`, `generation_queue_ae0522.feature`
- `backend/tests/unit/worker/test_worker_drain_ae0598.py`, `test_generation_worker_ae0522.py`
- `backend/tests/unit/scripts_ci/test_drain_generation_worker_ae0598.py`, `test_deploy_drains_worker_ae0598.py`,
  `test_deploy_generation_queue_ae0522.py`
- `backend/tests/integration/test_worker_drain_pg_ae0598.py`, `test_generation_queue_pg_ae0522.py`

## Test Evidence

See `.agent/reports/AE-0598.dev-summary.md` (AC → test map, GATES_JSON).

## QA Report

Pending.

## Decision Log

- Drain flag as a file in the worker's own `/tmp` tmpfs, not a Redis key or a DB row: no new volume or client, the
  deploy already `exec`s into the worker (healthcheck pattern), and a container restart starts without it.
- Idle signal from the worker's busy marker, not a `generation_runs` count: a stale `running` row of an earlier kill
  would hold the wait to its bound, and the marker is set before the drain check so no job slips past the deploy.
- Bound 240 s + stop grace 60 s keeps the old 300 s for the phase in flight while the deploy fits 15 minutes.

## Blockers

None.

## Final Summary

Pending (after merge and the first deploy).
