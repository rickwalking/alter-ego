# AE-0315 — Surface carousel revision-run progress instead of bare 409 conflicts

Status: Review
Tier: T3
Priority: High
Type: Feature
Area: cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

While a carousel revision/generation run is executing (~13–15 minutes
observed in prod), the client shows a live "revision in progress" state —
which phase is running, when it started, and that review actions are
temporarily unavailable — instead of enabled buttons that fail with an
opaque 409. Users (and operators) can tell a slow healthy run from a stuck
workflow at a glance.

## Problem

Prod incident (project `66014ba3`, 2026-07-10): a content revise ran
03:39→03:54 (LLM regeneration + slide writes + translations). During that
window:

- The UI showed no indication a run was active; the review buttons stayed
  enabled.
- Three user resume attempts got bare `409 Conflict`
  (`ensure_resume_not_in_progress`) with no client-side explanation.
- The situation was indistinguishable from a genuinely stuck workflow —
  it triggered an operator investigation, and a premature manual
  `phase_status` flip was applied to a healthy mid-flight run (risking a
  double-run race) because there was no signal separating "slow" from
  "stuck".

The `workflow/stream` SSE endpoint and `workflow_failure_alert` monitor
exist, but no run-progress signal reaches the create-flow UI.

## Scope

- Backend: persist `run_started_at` **and `run_heartbeat_at`** as new
  `carousel_projects` columns (Alembic migration; the watchdog must read
  them per tick without loading checkpoint state, and `updated_at` is
  overwritten by any row touch so it cannot serve). The background resume
  task heartbeats `run_heartbeat_at` at stage boundaries and at a fixed
  interval (e.g. every 60s) while alive. `run_started_at` is **cleared in
  the same UPDATE statement** that sets `phase_status` to any
  non-`in_progress` value (one atomic row write — a crash can never leave
  a terminal row with a live-looking run). **Enforced at the ORM layer,
  not per call site** (cold-critic r3: seven `phase_status` write sites
  exist and three bypass the write owner — the timeout repository, the
  phase-5 migration backfill, and the `update_from_entity` hydrator): a
  SQLAlchemy `before_update` listener on `CarouselProjectModel` clears
  `run_started_at`/`run_heartbeat_at` whenever `phase_status` **changes
  value** to a non-`in_progress` state (guarding the no-op-hydrate case so
  unrelated `update_project` calls never spuriously clear a live run's
  columns); a suite-wide assertion test verifies every non-in_progress
  transition clears them. Extend
  the workflow state response with run metadata when
  `phase_status = in_progress`: `run_started_at`, current phase, and a
  coarse `run_stage` (e.g. `generating`, `validating`, `persisting`)
  emitted by the run at stage boundaries.
- Backend: publish run lifecycle events on the existing SSE stream
  (`run.started`, `run.stage_changed`, `run.finished`) so the client
  updates live without polling.
- Backend: the resume 409 for an active run returns a typed detail
  (machine-readable code + `run_started_at`) distinct from the
  lock-version-conflict 409 and the revision-cap 409, so the client can
  render each case correctly.
- Backend: a **stale-run reaper keyed on liveness, not age** (cold-critic
  r2: age alone cannot distinguish a dead task from a slow-but-alive one —
  reaping a live run starts a second concurrent run, the exact split-brain
  the prod incident risked). The existing watchdog excludes `in_progress`
  rows and the in-flight stuck detector dies with the background resume
  task, so a restart/deploy mid-run leaves `in_progress` forever. Reaper
  rules:
  - Reap only rows where `phase_status = in_progress` (never otherwise,
    regardless of `run_started_at`) **and** the heartbeat is stale across
    **N consecutive watchdog observations** (default N=3; cold-critic r5:
    a single transient DB blip on the heartbeat UPDATE must not look like
    death). The in-task heartbeat write retries on failure. Where the
    dying task's asyncio handle is still known in-process, reaping also
    cancels it by reference (best-effort; the epoch fence is the
    correctness guarantee, task cancellation just stops wasted LLM
    spend).
  - **NULL heartbeat is alert-only, never reapable** (cold-critic r4: the
    column is new — a run alive across the deploy that added it has NULL
    forever from the reaper's view; reaping it on the first post-deploy
    tick is the exact live-run split-brain this design forbids). A row
    becomes reapable only after at least one non-NULL heartbeat has been
    observed and then gone stale. Pre-migration in_progress rows
    therefore only ever alert; genuinely dead pre-migration rows are
    cleared by the operator runbook (or the row's own run finishing),
    never automatically.
  - Cancellation is a **monotonic fencing token, not a boolean**
    (cold-critic r5: a per-project boolean cannot simultaneously reject
    the zombie and admit the replacement run — clearing it unblocks the
    zombie, keeping it deadlocks the replacement): a `run_epoch` integer
    column. Every run captures the epoch at start and stamps its writes;
    the reaper **increments the epoch** in the same flip UPDATE (alongside
    the `lock_version` bump). Guarded write paths compare the writer's
    captured epoch with the row's current epoch and reject on mismatch —
    the zombie's stale-epoch writes fail forever, the replacement run's
    current-epoch writes pass, no clearing step exists. **Enforcement is at the lowest shared layers, not at
    named service funnels** (cold-critic r4 refuted the 3-chokepoint
    claim: `PostgresCarouselRepository.update_project` alone commits the
    full write-owner column set directly for ~15 callers, and
    `activate_build` issues a raw UPDATE — service-level chokepoints do
    not cover the traffic). Enforcement layers:
    (a) a SQLAlchemy flush/commit-boundary guard (session event) that
    rejects mutations to `CarouselProjectModel`/`CarouselSlideModel` rows
    when the writer's captured `run_epoch` mismatches the row's current
    epoch — this covers every ORM commit path uniformly (the
    `update_project` funnel, slide writers, crud, scripts) with no
    per-site edits. **Run-ownership mechanism is explicit (cold-critic
    r6):** a `contextvar` (`carousel_run_epoch`) is set ONLY inside
    run-owned execution contexts (the background resume task, and the
    watchdog's reconciler stamping the current epoch); the flush guard
    compares only when the contextvar is set and passes otherwise —
    user-API and admin writes are never epoch-stamped (they are already
    gated by the 409/lock machinery) and can never be falsely rejected by
    a concurrent reap. Isolation note: the app runs Postgres default
    READ COMMITTED; guard correctness does not depend on isolation level
    because the comparison happens against the row's current value inside
    the flush transaction. Test: a non-run write concurrent with a reaper
    epoch bump succeeds; a run-owned write with a stale contextvar epoch
    is rejected;
    (b) the workflow engine's checkpoint-commit boundary (gating
    node-return application and `aupdate_state`);
    (c) explicit marker checks in the enumerated raw-SQL sites the ORM
    guard cannot see (`activate_build`'s direct UPDATE), plus a lint/grep
    gate banning new raw UPDATEs against these tables.
    **The write-site survey is a PRE-IMPLEMENTATION gate, not a
    completion artifact**: enumerate every `carousel_projects`/slide/
    checkpoint mutation site first (r4 verification counts ~30-34,
    including `update_project`'s ~15 callers, `activate_build`,
    `release_public`, crud routes, `reopen_carousel_for_resend`), map
    each to layer (a)/(b)/(c) or explicitly out-of-scope with rationale,
    and only then implement. Concurrent per-slide `asyncio.gather` work
    is gated at the same flush boundary (an individual in-flight slide
    write may complete; the next flush is rejected). Then reconcile against the
    checkpoint (checkpoint parked → flip row to match; checkpoint
    mid-step → reset to `awaiting_human` for a clean re-resume — where
    "clean" is defined at the checkpoint level (cold-critic r6): the
    reaper NEVER rewinds or edits checkpoint state; LangGraph resumes
    from the last node-boundary checkpoint, re-executing the interrupted
    node from its start, which is safe because side effects before
    `interrupt()` are idempotent by project rule (CLAUDE.md) — the
    re-resume test asserts a mid-generation reap + resume produces a
    complete, validated artifact, not a half-built one), **bump
    `lock_version` and `run_epoch` in the same UPDATE** (so any in-flight
    repair/resume holding the old version fails its CAS and any zombie
    write fails the epoch fence — this is the reap-vs-repair
    serialization; the reaper itself never needs the AE-0316 advisory
    lock), and emit `run.finished(stale)` + a `run_overdue` alert.
  - **Watchdog tick ordering is pinned** (cold-critic r5: the tick hosts
    both this reaper and AE-0311's drift reconciler): the reaper runs
    first; the drift reconciler runs only for rows the reaper did not
    touch this tick, and its convergence writes are tick-owned — they
    stamp the row's **current** epoch, so the fence never rejects the
    reconciler (a reaped project's drift is converged on the next tick
    under the new epoch).
  - Wall-clock age (default 60 min, above observed worst case) triggers
    the `run_overdue` **alert only**, never a reap by itself.
  This codifies the manual fix applied to prod project 66014ba3 while
  making it safe against slow healthy runs.
- Frontend: a stale-run escape hatch — when elapsed time exceeds the
  threshold, the banner offers "Check again", which refetches state (the
  reaper will have cleared genuinely dead runs) and re-enables actions
  when the run is no longer active. The UI is never permanently disabled.
- Frontend: the create flow renders the in-progress state on every step:
  banner with phase + elapsed time (started HH:MM), review actions
  disabled, live updates via the SSE events, automatic re-enable on
  `run.finished`.
- Frontend: if a 409 with the run-in-progress code still occurs (race),
  show the same banner instead of a generic error toast.

## Non-Goals

- No changes to run duration or LLM performance.
- No fine-grained token-level progress bars — coarse stages only.
- No changes to the existing `awaiting_human`-timeout auto-reject behavior
  (the new reaper only governs `in_progress` rows with stale heartbeats).
- No admin dashboard (create-flow UI only).

## Acceptance Criteria

- [ ] While a revision run is active, the create flow shows phase, start
      time, and elapsed time within 5 seconds of the run starting, on all
      steps, and disables approve/revise/edit actions.
- [ ] The state updates live through `generating` → `validating` →
      `persisting` and clears automatically when the run finishes
      (verified against a real or simulated run).
- [ ] Resume during a run returns the typed run-in-progress detail
      including `run_started_at`; the client renders the banner, not a
      generic error.
- [ ] The three 409 causes (run in progress, lock-version conflict,
      revision cap) are distinguishable by machine-readable code and have
      distinct client copy (pt-BR/en).
- [ ] A run exceeding the watchdog threshold logs `run_overdue` with
      project_id and elapsed minutes.
- [ ] Reaper: a `phase_status=in_progress` row whose owning task died
      (simulated backend restart mid-run — heartbeat goes stale) is
      reconciled by the watchdog tick within one interval past the
      heartbeat threshold — the cancellation marker is set first, the row
      returns to `awaiting_human`, `run.finished(stale)` is published,
      and a subsequent resume succeeds.
- [ ] Liveness safety: a slow-but-alive run (heartbeat fresh, wall clock
      past 60 min) is NEVER reaped — it only produces the `run_overdue`
      alert (test simulates a long run with active heartbeats).
- [ ] Fencing safety: a reaped task that revives cannot land writes
      (stale epoch fails at the SQLAlchemy flush boundary, the engine
      checkpoint-commit boundary, and the enumerated raw-SQL guards)
      while the replacement run's current-epoch writes succeed — one test
      exercises zombie-rejected AND replacement-accepted on the same
      project (the boolean-marker impossibility case).
- [ ] Heartbeat robustness: a single failed/missed heartbeat never causes
      a reap (N consecutive stale observations required, in-task retry
      covered by test).
- [ ] Pre-implementation write-site survey exists BEFORE marker code is
      merged: every mutation site enumerated and mapped to its
      enforcement layer or explicitly waived; a lint/grep gate bans new
      raw UPDATEs to the guarded tables.
- [ ] The reaper bumps `lock_version` and `run_epoch` in the same UPDATE
      that flips `phase_status`; an in-flight repair/resume holding the
      old version fails its CAS post-reap (test).
- [ ] Tick ordering: reaper before drift reconciler; the reconciler's
      convergence writes are never rejected by the epoch fence (test
      covers a project with both a stale heartbeat and drift).
- [ ] `run_started_at`/`run_heartbeat_at` are migrated `carousel_projects`
      columns; the ORM `before_update` listener clears them on every
      value-changing transition to a non-in_progress `phase_status`
      (covering the three owner-bypass sites), never on no-op hydrates;
      the watchdog reads both without loading checkpoint state.
- [ ] Reaper guard: rows with `phase_status != in_progress` are never
      reaped regardless of a leftover `run_started_at`; rows with a NULL
      `run_heartbeat_at` are alert-only (migration-day test: an
      in_progress row predating the column survives the first ticks and
      is never reaped).
- [ ] The banner is never permanent: past the threshold it offers
      "Check again", and after reaping the actions re-enable.
- [ ] Page reload during a run reconstructs the banner from workflow state
      (no dependency on having witnessed the SSE start event).

## Gherkin Scenarios

```gherkin
Feature: Revision-run progress visibility

  Scenario: User sees a live in-progress banner during a revision
    Given a content revision run was accepted
    When the user views any step of the create flow
    Then a banner shows the running phase and elapsed time
    And approve and revise actions are disabled

  Scenario: Resume attempt during a run explains itself
    Given a revision run is in progress
    When the client submits a resume request
    Then the response is 409 with a run-in-progress code and run_started_at
    And the UI shows the in-progress banner instead of an error toast

  Scenario: Banner clears when the run finishes
    Given the in-progress banner is visible
    When the run publishes run.finished on the workflow stream
    Then the banner clears and review actions re-enable
    And the regenerated content is shown

  Scenario: Overdue run is flagged for operators
    Given a run has exceeded the configured maximum duration
    When the workflow watchdog ticks
    Then a run_overdue alert is logged with the elapsed time

  Scenario: Dead run is reaped and the user recovers without an operator
    Given a backend restart killed a revision run mid-flight
    And the project row says in_progress with a stale run_heartbeat_at
    When the watchdog tick runs past the heartbeat threshold
    Then the cancellation marker is set before any row transition
    And the row is reconciled to awaiting_human
    And run.finished with a stale reason is published on the stream
    And the user's next resume attempt is accepted

  Scenario: Slow healthy run is alerted but never reaped
    Given a revision run alive for 70 minutes with fresh heartbeats
    When the watchdog tick runs
    Then a run_overdue alert is emitted
    And the row remains in_progress and the run continues undisturbed
```

## Delta

### ADDED

- Run metadata in workflow state (`run_started_at`, `run_stage`).
- `run.started` / `run.stage_changed` / `run.finished` SSE events.
- Typed 409 details distinguishing run-in-progress, version conflict, and
  revision cap.
- `run_overdue` watchdog alert + heartbeat-keyed stale-run reaper with
  cancellation marker (checkpoint-reconciling) in the workflow-workers
  tick.
- `carousel_projects.run_started_at`, `run_heartbeat_at`, and
  `run_epoch` columns (Alembic migration) — epoch is the fencing token.
- In-progress banner + action gating + stale-run "Check again" escape in
  the create flow.

### MODIFIED

- Resume 409 handling (typed details; response shape additive).
- Workflow state schema (additive fields).

### REMOVED

- Nothing.

## Affected Areas

- Backend: editorial workflow service (run lifecycle emission),
  `editorial_workflow_routes_validate.py` (typed 409s), workflow workers
  (watchdog), SSE stream publisher
- Frontend: create-flow shell (banner, action gating, SSE subscription,
  409 handling)
- Database: `carousel_projects.run_started_at`, `run_heartbeat_at`,
  `run_epoch` columns (Alembic migration)
- API: additive state fields + typed error details (OpenAPI regeneration)
- Tests: unit + `.feature` (behavior change); SSE integration test
- Docs: workflow guide (run lifecycle)
- Prompts/LLM: none
- Observability: `run_overdue` alert; stage timings measurable per phase
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: AE-0316 (typed conflict-detail schema for the three 409
  causes)
- Related: AE-0311 (repair 409 reuses the typed detail), AE-0314 (editor
  gating uses the same state), AE-0261 (resume/retry UX lane)

## Implementation Plan

1. Emit run lifecycle (started/stage/finished) from the resume execution
   path; persist `run_started_at` with `phase_status = in_progress`.
2. Typed 409 details for the three conflict causes.
3. Watchdog threshold in the existing workflow workers tick.
4. Frontend banner + gating + SSE subscription + reload reconstruction.
5. Integration test simulating a slow run; full gates.

## QA Checklist

- [ ] Security reviewed (no sensitive data in SSE events)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (reload mid-run, SSE reconnect, backend restart
      mid-run leaving stale in_progress)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (project 66014ba3: 15-minute
revision run indistinguishable from a stuck workflow; bare 409s; premature
operator intervention on a healthy run).

### 2026-07-10 — Development complete (wave worktree)

- **Pre-implementation write-site survey** (gate deliverable) written FIRST:
  `.agent/reports/AE-0315.write-site-survey.md` — 27 in-scope mutation sites
  (16 project ORM incl. the ~20-caller `update_project` funnel, 4 raw-SQL,
  4 slide, 3 checkpoint) mapped to layers (a)/(b)/(c) + enumerated OOS set.
- Alembic revision `b8c9d0e1f2a3` adds `run_started_at`, `run_heartbeat_at`,
  `run_epoch` (default 0); SQLite tests get the columns via `create_all`.
- ORM `before_update` listener (`carousel_run_guard.py`) stamps the run
  columns on the transition INTO `in_progress` and clears them atomically on
  every value-changing transition out (no-op hydrates guarded; suite-wide
  parametrized test covers all non-in_progress targets + the three
  owner-bypass sites: timeout `_reject`, phase-5 backfill, hydrator).
- Epoch fence: `carousel_run_epoch` contextvar (domain, run-owned contexts
  only) enforced at (a) the `before_flush` session boundary for
  project+slide rows (current-epoch read inside the flush txn, READ
  COMMITTED-safe), (b) the engine checkpoint-commit boundary
  (`ensure_checkpoint_commit_allowed` on start/resume/update_state via a
  domain DI seam), (c) explicit checks in `activate_build` + self-fencing
  WHERE clauses in the heartbeat write and reaper flip, plus the raw-UPDATE
  lint gate (`scripts/check_carousel_raw_updates.py`, AE-0180 rule-fires
  tests).
- Background resume task is run-owned: captures the fence at start,
  heartbeats every 60s with in-task retry, emits
  `generating`→`validating`→`persisting` stage boundaries and
  `run.finished(completed|failed)`; a fenced zombie logs
  `carousel_run_fenced` and exits without touching the row.
- Reaper (`carousel_run_reaper.py`) runs FIRST in the workers tick (AE-0311
  ordering hook left in place): in_progress-only, NULL heartbeat alert-only
  forever, N=3 consecutive stale observations (worker-scoped memory),
  wall-clock overdue (60 min) alert-only, ONE atomic flip UPDATE
  (checkpoint-reconciled status, lock_version+epoch bump, columns cleared),
  best-effort task cancel, `run.finished(stale)` + `run_overdue` logs.
- Typed 409: run-in-progress detail now carries `run_started_at`; state
  response gains additive `run_started_at`/`run_stage` (in_progress only);
  OpenAPI regenerated.
- Frontend: `CreateRunProgressBanner` on every create-flow step (phase,
  stage, started HH:MM, live elapsed, "Check again" past 5 min, never
  permanently disabled), SSE `run.*` subscription + state merge, reload
  reconstruction from state, run-in-progress 409 → banner not toast,
  distinct pt/en copy for all three 409 causes.

## Files Touched

Backend (new): `domain/constants/carousel_run.py`,
`domain/models/carousel_run.py`, `domain/protocols/carousel_run.py`,
`infrastructure/database/carousel_run_guard.py`,
`infrastructure/database/carousel_run_reaper.py`,
`modules/editorial/infrastructure/carousel_run_progress.py`,
`application/services/carousel/carousel_run_stage.py`,
`application/services/carousel/editorial_workflow_run_events.py`,
`bootstrap/carousel_run_reaper_factory.py`,
`alembic/versions/b8c9d0e1f2a3_add_carousel_run_progress_columns.py`,
`scripts/check_carousel_raw_updates.py`.

Backend (modified): `infrastructure/database/models/carousel.py` (+3
columns), `infrastructure/database/models/__init__.py` (guard re-export),
`infrastructure/database/carousel_artifact_build_repository.py` (layer-c
check), `agents/carousel_workflow_engine.py` (layer-b fence),
`application/services/carousel/editorial_workflow_resume_runner.py`
(run-owned context/heartbeat/stages/finish + cancel-by-reference),
`application/services/carousel/editorial_workflow_service.py` (run.started),
`application/workers/workflow_workers.py` (reaper-first tick +
`WorkflowWorkerServices`), `bootstrap/app_factory.py` (reaper wiring),
`infrastructure/config/settings.py` (4 reaper settings),
`api/routes/carousels/editorial_workflow.py` (run metadata overlay),
`api/routes/carousels/editorial_workflow_routes_response.py`
(`apply_run_metadata`), `api/routes/carousels/editorial_workflow_routes_validate.py`
(409 `run_started_at`), `api/schemas/carousel_workflow.py` (additive fields),
`docs/architecture/openapi.json` (regenerated),
`docs/backend/carousel-run-lifecycle.md` (new guide).

Backend tests: `tests/features/carousel_run_progress_reaper.feature` (new),
`tests/unit/infrastructure/test_carousel_run_guard.py` (new, 16),
`tests/unit/infrastructure/test_carousel_run_reaper.py` (new, 9),
`tests/unit/application/test_carousel_run_lifecycle.py` (new, 15),
`tests/unit/scripts_ci/test_carousel_raw_update_gate.py` (new, 7),
`tests/unit/agents/test_carousel_workflow.py` (re-resume test),
`tests/unit/application/test_workflow_workers.py` (new signature).

Frontend (new): `src/app/dashboard/create/workspace/create-run-progress-banner.tsx`
(+ its test).

Frontend (modified): `src/constants/editorial-workflow.ts` (run events,
stages, conflict codes, threshold), `src/modules/editorial/workspace/types-ai.ts`,
`hooks/types.ts`, `hooks/use-editorial-workflow-utils.ts` (run merge),
`hooks/use-editorial-workflow-sse.ts` (run.* subscription),
`hooks/use-editorial-workflow-resume.ts` (409 banner path + distinct copy),
`src/app/dashboard/create/workspace/create-workflow-panel.tsx` (banner on
every step), `src/i18n/locales/en.json` + `pt.json` (runProgress +
versionConflict/runInProgress errors), plus updated hook tests
(`use-editorial-workflow.test.ts`, `use-editorial-workflow-resume.test.ts`,
`use-editorial-workflow-utils.test.ts`).

Survey: `.agent/reports/AE-0315.write-site-survey.md`.

## Test Evidence

- Backend full unit suite:
  `uv run pytest tests/unit -q` →
  `2345 passed, 1 skipped, 25 warnings in 29.63s`
- `uv run mypy rag_backend/ --explicit-package-bases` →
  `Success: no issues found in 561 source files`
- `uv run ruff format --check src/` → `595 files already formatted`;
  `uv run ruff check src/` → `All checks passed!`
- `python3 scripts/metrics/import_baseline.py --check` → `RESULT: PASS`;
  `uv run lint-imports` → `Contracts: 22 kept, 0 broken.`;
  vulture clean; interrogate `PASSED (minimum: 80.0%, actual: 86.4%)`
- Frontend: `npx tsc --noEmit` → clean;
  `npx vitest run src/modules/editorial/workspace/hooks src/app/dashboard/create/workspace`
  → `Test Files 22 passed (22)`, `Tests 268 passed (268)`
- Rule-fires (AE-0180): seeded ORM-core + textual + slide-table violations
  each flagged; allowlisted file skipped; real tree clean.

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r6) — Cold-critic BLOCKER resolved: run-ownership contextvar + mid-step semantics

Round-6 demanded the mechanism distinguishing run-owned from user-owned
writes: pinned as a `carousel_run_epoch` contextvar set only in run-owned
contexts — the guard compares only when set, so user/admin writes can
never be falsely rejected by a concurrent reap (test added), and
correctness holds at READ COMMITTED. "Clean re-resume" defined: the
reaper never touches checkpoint state; LangGraph re-executes the
interrupted node whose pre-interrupt side effects are idempotent by
project rule.

### 2026-07-10 (r5) — Cold-critic BLOCKER resolved: epoch fencing token

Round-5 proved the boolean `run_cancelled` lifecycle unsolvable (clearing
it unblocks the zombie; keeping it deadlocks the replacement). Replaced
with a monotonic `run_epoch` fencing token: runs stamp writes with their
captured epoch, the reaper bumps it, stale-epoch writes fail forever and
current-epoch writes pass with no clearing step. Also: N=3 consecutive
stale heartbeat observations before reap (transient DB blips can't kill a
live run), best-effort asyncio cancel by reference, and pinned watchdog
tick ordering (reaper first; the drift reconciler's tick-owned writes
stamp the current epoch so the fence never blocks convergence).

### 2026-07-10 (r4) — Cold-critic BLOCKERs resolved: session-layer enforcement + NULL-heartbeat grace + reaper CAS

Round-4 refuted the 3-chokepoint claim (the `update_project` direct-commit
funnel carries ~15 callers; `activate_build` is raw SQL) and caught the
migration-day hazard (pre-deploy in_progress rows have NULL heartbeats and
would be reaped alive on the first tick). Resolutions: cancellation moves
to the SQLAlchemy flush boundary (uniform over all ORM paths) + engine
checkpoint boundary + explicit raw-SQL guards with a lint gate; the
write-site survey is a pre-implementation gate, not a completion
artifact; NULL heartbeats are alert-only until a heartbeat has been
observed; and the reaper bumps `lock_version` so in-flight repair/resume
CASes fail after a reap (reap-vs-repair serialization without the
advisory lock).

### 2026-07-10 (r3) — Cold-critic BLOCKER resolved: chokepoint gating + ORM-level invariant; retiered T3

Round-3 counted ~28 mutation sites across 6 layers — a per-site
cancellation sweep is untestable, and node-return dicts are implicit
writes a node-body check cannot gate. Resolution: enforce the marker at
the three write chokepoints (engine checkpoint-commit, project write
owner, slide asset writer), route known lateral bypasses through the
owner, and make the enumerated write-site survey a deliverable/completion
criterion. The `run_started_at` atomic-clear invariant moved to an ORM
`before_update` listener (three sites bypass the owner), guarded against
no-op hydrates. Typed-409 schema is consumed from AE-0316 (new
blocked-by). Ticket retiered T2→T3 to match the verified scope.

### 2026-07-10 (r2) — Cold-critic WARNs resolved: reaper liveness + terminal-write atomicity

Round-2 review showed the age-based reaper I added in r1 would reap
slow-but-healthy runs (no kill mechanism exists for the background resume
task) — automating the exact split-brain the ticket warns about.
Resolution: reaper is now keyed on a **stale heartbeat**
(`run_heartbeat_at`, new column), sets a cancellation marker every
mutation site checks before flipping the row, and wall-clock age only
alerts (60 min default), never reaps. `run_started_at` is cleared
atomically in the same UPDATE as any non-in_progress `phase_status` write,
and the reaper never touches non-in_progress rows.

### 2026-07-10 — Cold-critic BLOCKER resolved: stale-run reaper + run_started_at migration

External GLM 5.2 review verified the existing watchdog excludes
`in_progress` rows, the in-flight stuck detector dies with the resume task,
and no `run_started_at` exists — so the original plan would have produced a
permanently disabled UI after a backend restart mid-run (strictly worse
than today's bare 409). Resolution: scope now includes (a) a
checkpoint-reconciling stale-run reaper in the watchdog tick emitting
`run.finished(stale)`, (b) `run_started_at` as a migrated
`carousel_projects` column ("Database: none" corrected), and (c) a
frontend "Check again" escape so the banner is never permanent. Reaper AC
+ Gherkin added; this codifies the manual prod fix applied to 66014ba3.

## Blockers

None.

## Final Summary

Pending.
