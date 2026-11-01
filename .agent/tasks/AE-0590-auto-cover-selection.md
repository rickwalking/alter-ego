# AE-0590 — Use the autopilot's generated cover on slide 1

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro Marins
Branch: fix/ae-0590-auto-cover-selection
Created: 2026-11-01
Updated: 2026-11-01

## Goal

When the cover generation the autopilot started for a fresh carousel
succeeds, slide 1 uses that cover, unless the owner already chose a cover
for slide 1. A manual choice is never overridden.

## Problem

Owner report (2026-11-01): "the autopilot is creating new covers, but it is
not selecting the new cover as the one to be used." AE-0581 records one
generation and schedules the background run, which stores the image as a
private `cover` creator asset and settles the row `succeeded`. Nothing then
writes it to the carousel, so slide 1 keeps the default photo. The AE-0581
ticket listed "no automatic picking" as a non-goal; this ticket changes that.

## Findings (step 1, read before the fix)

- **How a manual generation becomes the cover:** never on its own. On
  success the publish step's options list refreshes (the frontend polls the
  generations list) and the generated asset shows up as a `generated` option.
  The owner then clicks it, which sends `PUT /carousels/{id}/cover` →
  `CoverPickService.pick` → `SlideCoverSwitchService.switch`. The Telegram
  "Usar capa do Grok" button only covers the topic's GrokBot cover
  (`cover_chosen` on the run), not generated covers.
- **Where the used cover is stored:** on the `carousel_projects` row.
  `slide_cover` (JSON: asset id, kind, staged path) is the chosen cover, and
  `hook_asset_id` is the slide-1 library photo. `current_cover_asset()`:
  `slide_cover.asset_id` if it is set, else `hook_asset_id`. A generated cover
  is stored as `slide_cover` with kind `ai_image`, staged into the project's
  render root.
- **How to tell the owner picked a cover:** nothing records a pick (no
  event, audit row or flag). The possible owner writes are:
  - the picker `PUT /cover`, accepted only when `status = completed`;
  - Telegram at the thesis step (`awaiting_thesis`), which sets
    `autopilot_runs.cover_chosen = true` and creates the project with
    `slide_cover` already set;
  - Telegram at the review step (`awaiting_owner`), for completed carousels
    only;
  - `PUT /carousels/{id}/hook-photo` (`select_hook_photo`), which has no
    phase check and rebinds `hook_asset_id` at any time.
  So the only way to see a manual choice is to compare the cover fields with
  their values when the generation was scheduled (baseline), together with
  `cover_chosen`.
- **Phase when the generation finishes:** `start_cover` runs right after
  `editorial.start` (research phase). The bridge allows up to 600 s plus a
  grace period, so the cover is usually ready while the workflow is still in
  research, outline or content, before images exist and well before
  `completed`. Selecting a cover at that point means recording `slide_cover`
  (and staging the file) so the finalize render uses it. No republish.
- **What the switch service's "republish" does:** `RepublishRenderer` →
  `republish_completed_carousel` → `finalize_carousel_after_images_approval`
  → `export_and_complete_carousel`. That chain re-renders the slides, runs the
  artifact health check, builds and activates a new artifact version (its own
  `lock_version` CAS), writes the PDF paths and calls
  `update_status(COMPLETED)`. It makes no Instagram, LinkedIn or Graph call,
  does not touch `is_public`/release, and does not resume the workflow. Two
  hazards:
  1. On a carousel that is not yet completed, it would mark the carousel
     `completed` and skip the images and final-review gates.
  2. On a completed carousel, the `lock_version` bump starts a new review
     revision. The owner's Telegram approve reads the *current* lock version
     (`FinalReviewApproval.approve`), so the owner could approve a cover they
     never saw, and a carousel that is already `scheduled` would go out with an
     image the owner did not approve.
  The auto-selection therefore never calls the renderer.
- **Race with the workflow:** `update_project` writes `slide_cover` and
  `hook_asset_id` from the entity it is given on every save
  (`write_owner_edits`). The image node keeps one project entity for the whole
  image phase and saves it on each progress report, so a write that lands
  mid-phase is silently reverted. A `lock_version` bump during finalize would
  also break the artifact-activation CAS. The selection is therefore written
  only while the workflow is paused at a gate (`phase_status` is not
  `in_progress`).
- **Telling autopilot generations apart without a schema change:** the
  generation row has no origin column. The autopilot schedules its run
  through its own code path (`carousel_cover_autostart._schedule`), so the
  selection is attached to that task only. The HTTP route's
  `cover_generation_task` stays as it is. The run is in-process, and a restart
  kills it (the row is then failed as interrupted), so no generation can
  succeed outside its own task. No schema change is needed.

## Scope (design)

- `schedule_autopilot_cover` captures a baseline from the project it already
  loads: `slide_cover` asset id and `hook_asset_id`. It schedules a task that
  runs the unchanged `CoverGenerationRunner` and, only when that returns
  `SUCCEEDED`, runs the auto-selection on a fresh session.
- Auto-selection (new editorial module), on a fresh session:
  1. Wait, bounded, for a safe point: re-read the project every few seconds
     until `phase_status != in_progress`. Give up when the deadline passes or
     the carousel is `completed`.
  2. Guards, each a logged skip: project gone; the carousel is `completed` or
     `failed` (owner review already started, or the run is over); the
     autopilot run is not `generating` or has `cover_chosen = true`; the
     baseline had a `slide_cover`; the current `slide_cover` or
     `hook_asset_id` differs from the baseline (a manual choice); the
     generated asset or its file is gone. If `slide_cover` already is the
     generated asset, the run is a no-op (idempotent).
  3. Write through the unchanged `SlideCoverSwitchService`: stage the file,
     then project advisory lock + `lock_version` CAS at the version just read,
     then store `slide_cover` (kind `ai_image`). It uses a no-op renderer, so
     there is no republish, no status change and no publish.
  4. On a CAS conflict or a held lock: skip and log. Never retry, never force.
- A failed or refused generation never calls the selection. The current
  cover is left alone.
- Manual generations (HTTP route) keep today's behavior.

## Non-Goals

- No schema or migration change.
- No change to the picker, the Telegram cover buttons, the caps, consent,
  prompts or publish code.
- No auto-selection on a carousel that is already completed. It waits for
  Pedro's decision after the prod probe. Today's behavior applies: the cover
  shows up in the picker.

## Acceptance Criteria

- [ ] A succeeded autopilot generation becomes slide 1's `slide_cover`
      (`ai_image`) when the owner made no choice, written while the workflow
      is paused at a gate.
- [ ] A manual choice made after scheduling (hook photo rebind, a
      `slide_cover`, `cover_chosen`) is never overridden; the skip is logged.
- [ ] A failed or refused generation leaves the current cover alone.
- [ ] Idempotent: re-running the selection for the same asset changes
      nothing.
- [ ] No publish and no approval bypass: the selection never calls the
      republish renderer, never changes status, never touches
      Instagram/LinkedIn (a test asserts no renderer or publish call).
- [ ] Lock-version CAS unchanged: on a conflict the selection skips and logs,
      with no retry (a test asserts it).
- [ ] Manual (HTTP) generations are never auto-selected.
- [ ] Backend gates green (hotfix fast path: every gate except local
      mutation, individually, with `DATABASE_URL`; Python 3.11 import check);
      CI green before merge (no `--admin`).

## Repro Steps

1. With `AUTOPILOT_COVER_CONSENT` on, let the autopilot start a POV carousel.
2. The cover generation succeeds (`carousel_cover_generations.status =
   succeeded`, `result_asset_id` set).
3. The carousel's `slide_cover` stays NULL, so slide 1 keeps the default
   photo.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0581 (autopilot auto-cover start).

## Progress Log

### 2026-11-01

Ticket created (hotfix, Pedro 2026-11-01). Step 1 findings recorded above. A
read-only prod probe (outside the repo) was handed to the lead; the fix waits
for the probe output and the go-ahead.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
