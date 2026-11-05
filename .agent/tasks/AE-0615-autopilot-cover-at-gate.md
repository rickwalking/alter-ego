# AE-0615 — Put a succeeded autopilot cover on slide 1 before the first final review

Status: Dev Complete
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Claude
Agent Lane: developer → qa → release
Branch: fix/ae-0615-autopilot-cover-autoselect
Kanban Card: TBD
Created: 2026-11-04
Updated: 2026-11-04

## Goal

When the autopilot's own cover generation succeeds before the carousel reaches its final review, the owner's
first final review already shows that cover on slide 1. An owner's own choice is never overwritten.

## Problem

Prod, 2026-11-04, carousel `9aaf2096`, run `facfa460`, `AUTOPILOT_COVER_CONSENT=true` (8-char prefixes):

- 12:05:56Z the autopilot started cover generation `62547839` (`autopilot.cover outcome=auto_started`). It
  succeeded at 12:07:36Z with asset `a2367f6f`. The carousel was in research.
- The autopilot drive then ran outline, content, design, images and final_review back to back.
- 12:38:08.747Z `cover_auto_select outcome=skipped reason=carousel_completed generation_id=62547839`. No
  later attempt.
- 12:38:55Z the final review went out with `slide_cover` empty, 31 min after the cover succeeded. The owner
  set the cover by hand on the website at 12:41:42Z (`PUT /api/carousels/{id}/cover`).

Prod, same day, carousel `d418daf9`, run `77a6593b`:

- Cover generation `ab9f19c0` was created at 13:16:46Z and succeeded at 13:18:25Z (asset `2467d172`) in the
  old containers.
- 13:39:49Z: a deploy restarted the backend and the generation worker. The drive was reaped and resumed at
  13:43:28Z.
- No `cover_auto_select` outcome was ever logged for it after the restart. It reached
  final_review/awaiting_human at 14:20Z with `slide_cover` empty. Deploys happen several times a day and a
  drive takes 30-60 min, so this case is common.

## Root Cause (verified)

Three paths lose the cover. All three come from the same design: the only actor is an in-process
background wait.

1. **The drive never pauses where the poll can see it** (carousel `9aaf2096`).
2. **A conflict is never retried.** A held lock or a moved version at the one pause the poll catches
   ends the selection for good.
3. **A restart loses the task** (carousel `d418daf9`). The wait runs inside the in-process background task.
   A deploy kills it, and nothing re-creates it.

Details:

- The background selection (`selecting_cover_task` → `with_cover_selection` →
  `AutoCoverSelector.select`, `application/services/carousel/cover_autoselect.py:229`) waits in `_paused`
  (`:273-289`). It re-reads the project every 5 s for up to 45 min and writes only once
  `phase_status != in_progress`. A carousel at `final_review` or `completed` is a permanent skip
  (`_phase_refusal`, `:175-178`, `carousel_completed`). A conflict or a held lock is a skip that is never
  retried (`_settle`, `:268-271`).
- The autopilot drive (`modules/generation_queue/application/executors.py:152-167`) steps the runner in a
  loop. At each gate the runner reads the paused snapshot and resumes it in the same step
  (`AutopilotRunner._approve` → `_resume`, `modules/autopilot/application/runner.py`). The pause lasts
  only from the gate read to the resume, which is shorter than the 5 s poll interval. So the poll almost
  never sees a pause. The first settled state it reads is the final review, and that is a permanent skip.
  The prod log line above shows exactly this.
- The background task is in-process (`schedule_cover_generation`, `asyncio.create_task`). The owner-choice
  baseline (slide 1's cover fields at scheduling) was held only in that task's closure, so after a restart
  neither the task nor the baseline exists any more.
- The AE-0590 tests (`tests/integration/test_autopilot_cover_autoselect_pg_ae0590.py`, seed at `:174-180`)
  start from a carousel that is already paused at the content gate, so the drive-through case was never
  tested.

## Decision: Option A, at the gate

The drive itself always stands at a gate (paused, `awaiting_human`) before it resumes. In `_resume`, the
runner first asks for the carousel's succeeded autopilot cover. If slide 1 took it, the step ends and the
next step reads the gate again at the new lock version, then resumes. The selection is the existing one,
run once without waiting, with the same checks and the same write: the generation's own asset on this
carousel (`_generated_asset`), the owner-choice baseline (`choice_refusal` plus the conditional UPDATE on
the committed row), the project lock and the lock-version CAS. It runs before the finalize render (images
approval), so the first final review shows the cover with no re-render and no second review. It writes
nothing without `AUTOPILOT_COVER_CONSENT`.

Everything the gate needs is durable. When the autopilot schedules its generation, it writes one row in the
new table `carousel_cover_autopilot_baselines`, in the same transaction as the generation row
(`AutopilotCoverGenerationRepository.create` adds it to the service's one flush and commit). So either both
rows exist or neither does. A failed baseline write therefore leaves no generation stuck in `pending`, which
would count against the caps and block the one-per-carousel retry.
The row holds the generation id (FK, cascade), plus slide 1's `slide_cover` asset id and `hook_asset_id` at
that moment. Asset ids are plain columns with no FK, so a deleted asset does not erase the record. At each
gate, `select_cover_at_gate` reads the carousel's newest generation that is succeeded, has a result asset
and has a baseline row, and runs the selection with that baseline. Nothing is held in process memory:

- a restart between the cover's success and the next gate changes nothing;
- a conflict is simply asked again at the next gate;
- a cover already in place is an `already_selected` no-op.

An owner's own pick made after the job was scheduled differs from the recorded baseline. The selection
refuses it (`manual_choice`), and the conditional UPDATE re-checks it on the committed row, across any
restart. Nothing depends on the planned owner-pick audit (AE-0616).

Why a new table, not new columns on `carousel_cover_generations`: production adds new tables through the
app's startup `create_all` (and the Alembic revision on deploy, ADR-012). A new column on an existing table
would need a deploy one-shot script and a `deploy.yml` step, and every read of the generation rows would
fail until it ran. The revision `b2c3d4e5f6a8` is additive and idempotent, and the schema-drift and
migrations gates cover it.

Why not at the final-review stop (`runner._stop`), as option A was first written: at that point the slides
are already rendered. Writing `slide_cover` there without a render would send a review whose slide 1 does
not match the stored cover. Rendering there is the review switch, which is option B.

Why not option B (a `ReviewSwitch` on autopilot selections): it fires only after the carousel reached
the final review. It re-renders and holds or re-sends the Telegram review, so the owner's first review
would still show the default slide 1, or a second review would follow. The goal is that the first review
already shows the cover.

## Scope

- `carousel_cover_autopilot_baselines` table (model, constant, Alembic revision `b2c3d4e5f6a8`).
- `SqlCoverGenerationRepository.record_autopilot_baseline` / `autopilot_selection`.
- `AutopilotCoverGenerationRepository` (the generation rows plus the baseline row in one transaction).
  `cover_generation_service` takes an optional store. The background task and the manual website path are
  unchanged.
- `carousel_cover_gate_select.select_cover_at_gate` (editorial infrastructure): one selection without
  waiting, from the database.
- `AutoCoverApplier` port and `cover_at_gate` (autopilot domain). `RunnerDependencies.cover_apply`.
  `AutopilotRunner._resume` asks first. `EditorialAutoCoverScheduler.apply_cover` checks consent first and
  logs a crash instead of raising it. Bootstrap wires the same scheduler to both ports.

## Non-Goals

- No change to validators, gates, limits, timeouts, the poll window, consent rules or the review switch.
- No change to the manual "Gerar capa com Grok" path or to the website review switch (AE-0594).
- A cover that succeeds only after the images gate was approved still stays a picker option (AE-0590
  non-goal, unchanged).
- No prod data change, no backfill: generations scheduled before this deploy have no baseline row and
  keep today's behaviour.

## Acceptance Criteria

- [x] A drive straight through to the final review, with a cover that succeeded during research, ends with
      `slide_cover` = that asset, kind `ai_image`, before the final review.
- [x] An owner's own choice made before the gate (photo rebound, or a cover chosen before the job) is
      never overwritten.
- [x] Without consent nothing is read or written.
- [x] A failed generation leaves slide 1 untouched.
- [x] A conflict at a gate is retried at the next gate. A crash never breaks the drive.
- [x] A restart between the cover's success and the next gate still puts the cover on slide 1 before the
      first final review.
- [x] An owner's pick made after the generation was scheduled is kept across a restart.
- [x] Touched tests and the cheap backend gates pass.

## Gherkin Scenarios

`backend/tests/features/autopilot_cover_gate_select_ae0615.feature`

```gherkin
Feature: The autopilot puts its succeeded cover on slide 1 at the next gate (AE-0615)

  Scenario: A drive straight through to the final review shows the cover
  Scenario: A restart before the next gate still shows the cover
  Scenario: An owner's pick made after scheduling is kept across a restart
  Scenario: A failed baseline write leaves no stuck generation
  Scenario: The drive stores the cover at a gate before it resumes
  Scenario: The owner's photo chosen before the gate is kept
  Scenario: A cover the owner chose before the job is kept
  Scenario: Without consent the drive stores nothing
  Scenario: A failed generation leaves slide 1 alone
  Scenario: A conflict at the gate is tried again at the next gate
  Scenario: A crash while storing the cover never breaks the drive
```

## Delta

### ADDED

- `modules/editorial/infrastructure/carousel_cover_gate_select.py`.
- Table `carousel_cover_autopilot_baselines` (`CarouselCoverAutopilotBaselineModel`,
  `TABLE_COVER_AUTOPILOT_BASELINES`, revision `b2c3d4e5f6a8`).
- `SqlCoverGenerationRepository.record_autopilot_baseline` / `autopilot_selection`.
- `AutoCoverApplier`, `cover_at_gate`, `RunnerDependencies.cover_apply`,
  `EditorialAutoCoverScheduler.apply_cover`, `ACTION_APPLY_COVER`.
- Editorial facade export `select_cover_at_gate`.

### MODIFIED

- `carousel_cover_autostart._record_generation`: starts the generation through
  `AutopilotCoverGenerationRepository`, so the baseline row lands in the same commit.
- `select_cover_at_gate` takes the scheduler's injected session factory.
- `AutopilotRunner._resume`: asks for the cover before it resumes a gate.
- `autopilot/bootstrap.runner_dependencies`: one scheduler for both ports.
- `editorial/public.py` docstring: shortened two lines so the file stays at 400.
- Tests: `test_autopilot_cover_autostart_pg_ae0581.py` creates the new table in its isolated schema;
  the fake repository in `test_cover_autostart_editorial_ae0581.py` takes the baseline;
  `test_autopilot_migration.py` moves the single head to `b2c3d4e5f6a8`.

### REMOVED

- Nothing.

## Affected Areas

- Backend: editorial cover selection, autopilot runner and bootstrap
- Tests: new feature, unit and Postgres tests
- Database: one new table (additive Alembic revision, created at startup by `create_all`)
- Frontend / API / Deployment: none

## Dependencies

- Related: AE-0590 (background selection), AE-0581 (autopilot cover start), AE-0594 (website review switch)

## Implementation Plan

1. Verify the root cause.
2. `.feature`, then tests that fail on main.
3. Fix.
4. Touched and related tests, cheap gates, PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-11-04

Root cause verified in the code against the prod log. Red before the fix: all 12 new tests failed on main.
The Postgres drive-through ends with `slide_cover` empty (`assert isinstance(row.slide_cover, dict)`). The
other Postgres tests have no gate answer (`assert [] == [('research', ...)]`). The unit tests fail because
`cover_apply` and `apply_cover` do not exist. Green after the fix, plus the related cover, runner and
executor tests (413).

Restart path (prod `d418daf9`). The first version held the selection in process memory, and a deploy lost
it. Two new Postgres tests restart between the cover's success and the next gate: the background wait ends
without a read and the gate module is loaded afresh. Red on the PR head `f8fe92a3` (fix version 1):

- the restart test ends with `slide_cover` empty (`assert isinstance(row.slide_cover, dict)`);
- the owner-pick test finds no gate check at all (`assert set() == {'manual_choice'}`).

Green after the durable baseline. Touched and related tests plus every migration test: 392 passed.

Review follow-up. The baseline row moved into the generation's own transaction. Red first: a failed baseline
write left one pending generation (`assert (CoverGeneration(...),) == ()`). The Postgres tests were split
into `test_autopilot_cover_gate_select_pg_ae0615.py`, `test_autopilot_cover_gate_restart_pg_ae0615.py` and
the shared `cover_gate_pg_support.py`, with no test removed. The `object` annotations in the new tests are
gone. The gate uses the injected session factory. Result: 393 passed.

## Files Touched

See `.agent/reports/AE-0615.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0615.dev-summary.md`. Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- 2026-11-04: option A at the gate, not at the final-review stop and not option B (see Decision).
- 2026-11-04: the selection and the owner-choice baseline move from process memory to the database (new
  table `carousel_cover_autopilot_baselines`), because a deploy between the cover's success and the next
  gate lost them in prod (`d418daf9`). A new table, not new columns, so no deploy one-shot is needed.
- 2026-11-04 (review): the baseline row is written in the generation's transaction, not in a second commit.
  A failed write must not leave a pending generation that blocks the carousel's cover.

## Blockers

None.

## Final Summary

Pending.
