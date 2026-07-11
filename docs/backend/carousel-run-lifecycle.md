# Carousel run lifecycle: progress visibility, heartbeats, and the stale-run reaper (AE-0315)

While a carousel revision/generation run executes (~13–15 minutes observed in
prod), the system persists and broadcasts run progress so the client shows a
live "revision in progress" state instead of enabled buttons that 409, and
operators can tell a slow healthy run from a dead one.

## Columns (`carousel_projects`, migration `b8c9d0e1f2a3`)

| Column | Semantics |
|--------|-----------|
| `run_started_at` | Stamped when `phase_status` transitions INTO `in_progress`; cleared atomically (same flush UPDATE) on any value-changing transition out. Enforced by the `before_update` listener in `infrastructure/database/carousel_run_guard.py`, never per call site. |
| `run_heartbeat_at` | Heartbeaten by the background resume task every 60s (`DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS`) and at stage boundaries, with in-task retry. NULL = pre-migration run → alert-only forever. |
| `run_epoch` | Monotonic fencing token. Runs capture it at start into the `carousel_run_epoch` contextvar; ONLY the reaper increments it. |

## Epoch fence (zombie-run serialization)

The contextvar is set only in run-owned contexts (the background resume task
and its heartbeat). Enforcement layers (see
`.agent/reports/AE-0315.write-site-survey.md` for the full site map):

- **(a) flush boundary** — `before_flush` session guard rejects
  `CarouselProjectModel`/`CarouselSlideModel` mutations whose captured epoch
  mismatches the row's current epoch (`StaleRunEpochError`). Contextvar unset
  → pass, so user/admin/operator writes are never falsely rejected.
- **(b) checkpoint-commit boundary** — `CarouselWorkflowEngine`
  `start`/`resume`/`update_state` call `ensure_checkpoint_commit_allowed`
  (domain seam; reader registered by infrastructure).
- **(c) raw-SQL sites** — explicit epoch checks / self-fencing WHERE clauses
  in `activate_build`, the heartbeat write, and the reaper flip; the lint
  gate `backend/scripts/check_carousel_raw_updates.py` (rule-fires test in
  `tests/unit/scripts_ci/test_carousel_raw_update_gate.py`) bans new raw
  UPDATEs against the fenced tables.

## Stale-run reaper (workflow-workers tick, runs FIRST)

Rules (`infrastructure/database/carousel_run_reaper.py`):

- Considers only `phase_status == in_progress` rows.
- NULL heartbeat → alert-only forever (`carousel_run_null_heartbeat_alert`).
- Reap requires N=3 consecutive stale observations
  (`workflow_run_reap_observations`; staleness threshold
  `workflow_run_heartbeat_stale_seconds`, default 180s). Counts live in
  worker memory — a restart just delays a reap by up to N ticks.
- Wall clock past `workflow_run_overdue_minutes` (default 60) → `run_overdue`
  alert only, never a reap.
- The flip is ONE atomic UPDATE: `phase_status` reconciled against the
  checkpoint (parked → mirrored; mid-step → `awaiting_human`), `lock_version`
  AND `run_epoch` bumped, run columns cleared. In-flight repair/resume CASes
  holding the old version fail after the reap.
- The reaper NEVER touches checkpoint state: on re-resume LangGraph re-executes
  the interrupted node from its start (pre-`interrupt()` side effects are
  idempotent by project rule).
- Best-effort in-process `asyncio` task cancel by reference; the epoch fence
  is the correctness guarantee.
- Tick ordering is pinned: reaper first; the AE-0311 drift reconciler runs
  after it (hook comment in `application/workers/workflow_workers.py`).

## Surfaces

- **SSE** (existing workflow stream): `run.started` (phase +
  `run_started_at`), `run.stage_changed` (`generating`/`validating`/
  `persisting`), `run.finished` (`completed`/`failed`/`stale`).
- **State response** (`GET /carousels/{id}/workflow/state`): additive
  `run_started_at` + `run_stage`, populated only while `in_progress` — the
  create flow reconstructs the banner on reload from state alone.
- **Typed 409**: the run-in-progress conflict detail carries
  `run_started_at`; the client renders the banner, not a toast. The three
  409 causes (run in progress / version conflict / revision cap) have
  distinct machine codes and distinct pt/en copy.
- **Frontend**: `create-run-progress-banner.tsx` on every create-flow step;
  "Check again" escape past 5 minutes (`EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS`)
  refetches state — the UI is never permanently disabled.

Gherkin: `backend/tests/features/carousel_run_progress_reaper.feature`.
