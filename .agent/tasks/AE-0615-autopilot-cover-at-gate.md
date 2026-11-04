# AE-0615 — Put a succeeded autopilot cover on slide 1 before the first final review

Status: In Development
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

## Root Cause (verified)

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

The baseline (slide 1's cover fields when the job was scheduled) is not persisted anywhere. The autopilot's
task remembers the succeeded selection in the worker process, which is the one that runs the drive. A
conflict, a held lock or a wait that ran out keeps it for the next gate. Any other outcome forgets it. A
restart loses it, which is the same limit the background wait already has. No schema change.

Why not at the final-review stop (`runner._stop`), as option A was first written: at that point the slides
are already rendered. Writing `slide_cover` there without a render would send a review whose slide 1 does
not match the stored cover. Rendering there is the review switch, which is option B.

Why not option B (a `ReviewSwitch` on autopilot selections): it fires only after the carousel reached
the final review. It re-renders and holds or re-sends the Telegram review, so the owner's first review
would still show the default slide 1, or a second review would follow. The goal is that the first review
already shows the cover.

## Scope

- `carousel_cover_gate_select` (editorial infrastructure): `remembering_cover_task` (the autopilot's task:
  generate, remember on success, background selection, settle) and `select_cover_at_gate` (one selection
  without waiting).
- `carousel_cover_autostart._schedule` uses `remembering_cover_task`. The manual website path is unchanged.
- `AutoCoverApplier` port and `cover_at_gate` (autopilot domain). `RunnerDependencies.cover_apply`.
  `AutopilotRunner._resume` asks first. `EditorialAutoCoverScheduler.apply_cover` checks consent first and
  logs a crash instead of raising it. Bootstrap wires the same scheduler to both ports.

## Non-Goals

- No change to validators, gates, limits, timeouts, the poll window, consent rules or the review switch.
- No change to the manual "Gerar capa com Grok" path or to the website review switch (AE-0594).
- A cover that succeeds only after the images gate was approved still stays a picker option (AE-0590
  non-goal, unchanged).
- No prod data change.

## Acceptance Criteria

- [x] A drive straight through to the final review, with a cover that succeeded during research, ends with
      `slide_cover` = that asset, kind `ai_image`, before the final review.
- [x] An owner's own choice made before the gate (photo rebound, or a cover chosen before the job) is
      never overwritten.
- [x] Without consent nothing is read or written.
- [x] A failed generation leaves slide 1 untouched.
- [x] A conflict at a gate is retried at the next gate. A crash never breaks the drive.
- [x] Touched tests and the cheap backend gates pass.

## Gherkin Scenarios

`backend/tests/features/autopilot_cover_gate_select_ae0615.feature`

```gherkin
Feature: The autopilot puts its succeeded cover on slide 1 at the next gate (AE-0615)

  Scenario: A drive straight through to the final review shows the cover
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
- `AutoCoverApplier`, `cover_at_gate`, `RunnerDependencies.cover_apply`,
  `EditorialAutoCoverScheduler.apply_cover`, `ACTION_APPLY_COVER`.
- Editorial facade export `select_cover_at_gate`.

### MODIFIED

- `carousel_cover_autoselect`: `_select` is now `select_logged` and returns the outcome. The selection is
  built by `cover_selection`.
- `carousel_cover_autostart._schedule`: the autopilot task remembers a succeeded cover.
- `AutopilotRunner._resume`: asks for the cover before it resumes a gate.
- `autopilot/bootstrap.runner_dependencies`: one scheduler for both ports.
- `editorial/public.py` docstring: shortened two lines so the file stays at 400.
- `test_cover_autoselect_task_ae0590.py`: its wiring test now follows the autopilot task.

### REMOVED

- Nothing.

## Affected Areas

- Backend: editorial cover selection, autopilot runner and bootstrap
- Tests: new feature, unit and Postgres tests
- Frontend / Database / API / Deployment: none

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

## Files Touched

See `.agent/reports/AE-0615.dev-summary.md`.

## Test Evidence

See `.agent/reports/AE-0615.dev-summary.md`. Full gate: lead's heavy slot. Mutation: CI only.

## QA Report

Pending.

## Decision Log

- 2026-11-04: option A at the gate, not at the final-review stop and not option B (see Decision).

## Blockers

None.

## Final Summary

Pending.
