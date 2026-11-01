# AE-0590 — Use a generated cover on slide 1

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

When a cover generation succeeds, the one the autopilot starts for a fresh
carousel or the owner's "Gerar capa com Grok", slide 1 uses that cover,
unless a cover was already chosen or the owner chose one while the job ran.
A manual choice is never overridden. A carousel already completed or at final
review keeps its cover; the generated one stays a picker option.

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
  succeed outside its own task. No schema change is needed. (Superseded by
  Pedro's decision of 2026-11-01, below: manual generations select too, so
  both paths now share one task wrapper.)

## Scope (design)

- `schedule_autopilot_cover` captures a baseline from the project it already
  loads: `slide_cover` asset id and `hook_asset_id`. It schedules a task that
  runs the unchanged `CoverGenerationRunner` and, only when that returns
  `SUCCEEDED`, runs the auto-selection on a fresh session.
- Auto-selection (new editorial module), on a fresh session:
  1. Wait, bounded, for a safe point: re-read the project every few seconds
     until `phase_status != in_progress`. Give up when the deadline passes or
     the carousel is `completed`.
  2. Guards, each a logged skip: project gone; the carousel is `completed`,
     at `final_review` or `failed` (owner review already started, or the run
     is over); the baseline had a `slide_cover` (the owner's thesis-time
     GrokBot choice, which is what `cover_chosen = true` produces); the
     current `slide_cover` or `hook_asset_id` differs from the baseline (a
     manual choice); the generated asset or its file is gone. If
     `slide_cover` already is the generated asset, the run is a no-op
     (idempotent). The autopilot run state is not read: editorial must not
     import autopilot, and the picker and the review-time Telegram button
     only act on completed carousels, which are already skipped.
  3. Stage the file, then, under the project advisory lock and the unchanged
     `lock_version` CAS (`write_locked`) at the version just read, run one
     conditional UPDATE that sets only `slide_cover` (kind `ai_image`)
     `WHERE slide_cover IS NULL (or JSON null) AND hook_asset_id IS NOT
     DISTINCT FROM <baseline>`. `hook_asset_id` is never written. No
     renderer is called: no republish, no status change, no publish. When the
     UPDATE matches no row (an owner write that takes no lock, such as
     `PUT /hook-photo`, landed after the re-check), the CAS bump is rolled
     back and the skip reason is `manual_choice`.
  4. On a CAS conflict or a held lock: skip and log. Never retry, never force.
  5. Skips for a lost row (`no_result`, `no_project`) and for `timed_out`
     log at warning; the others at info. A `rejected` or `failed`
     `phase_status` ends the wait like a failed carousel.
- `PUT /carousels/{id}/hook-photo` (`select_hook_photo`) now clears
  `slide_cover`, as the picker already does for a library photo, so the
  owner's latest slide-1 photo wins over a stored generated cover. The
  frontend does not call this route (API only), and the create-time bind
  runs on a project with no cover, so nothing else changes. A run whose
  owner chose the topic's GrokBot cover on Telegram keeps
  `cover_chosen = true` after such a rebind; that flag only drives the
  Telegram keyboard.
- Known limit: the wait runs inside the in-process background task, so a
  restart or a deploy while it waits loses the selection. The cover then
  stays a picker option, which is today's behavior.
- A failed or refused generation never calls the selection. The current
  cover is left alone.
- Manual generations (Pedro, 2026-11-01): the HTTP route's run goes through
  the same wrapper (`selecting_cover_task`), with the baseline taken from the
  project the request loaded, under the same rules. If the owner clicks Grok
  while a cover is already chosen, `slide_cover` is set at scheduling and
  the `owner_cover` rule keeps it: an existing chosen cover wins.

## Non-Goals

- No schema or migration change.
- No change to the picker, the Telegram cover buttons, the caps, consent,
  prompts or publish code.
- No auto-selection on a carousel that is already completed or at final
  review (Pedro, 2026-11-01): no re-render and no re-approval; the
  generated cover stays a picker option.

## Acceptance Criteria

- [ ] A succeeded generation (autopilot or "Gerar capa com Grok") becomes
      slide 1's `slide_cover`
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
- [ ] A manual generation follows the same rules: selected on a paused
      carousel; an already chosen cover is kept; on a completed carousel it
      is only a picker option.
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
read-only prod probe (outside the repo) was handed to the lead.

Probe result (lead, prod): none of the 5 latest autopilot carousels with a
generation had an auto-started one. AE-0581 deployed 2026-10-31 20:07Z with
`AUTOPILOT_COVER_CONSENT=true`, and no autopilot carousel was created after
it, so the auto-start path has not run on prod yet. The reported generations
were manual: each was applied by the owner through `PUT .../cover`. Go-ahead
given for the design as proposed: autopilot-started generations only, only on
`succeeded`, only while paused at a gate, never a republish, and a cover that
finishes after completion stays a picker option. Whether manual generations
should auto-select too is an open question for Pedro (a possible follow-up).
`slide_cover` is read only through the existing entity path
(`slide_cover_from_row`), never with JSON SQL operators.

Implemented: `application/services/carousel/cover_autoselect.py` (selector,
baseline, owner-choice rules, bounded wait for a gate);
`modules/editorial/infrastructure/carousel_cover_autoselect.py` (fresh-session
store, the locked conditional write, the succeeded-only task wrapper); the
autostart wraps its own task with the scheduling baseline.

Review fixes (lead review, nothing blocking): the write no longer goes through
`SlideCoverSwitchService` (whose re-read could reuse a cached project and
write a stale `hook_asset_id` back). It is now a conditional UPDATE of
`slide_cover` alone inside the unchanged lock + CAS (`render=False` was
removed again). `PUT /hook-photo` clears `slide_cover`. A `rejected` or
`failed` `phase_status` is a skip. The generation task is typed
`CoverGenerationStatus`. Lost-row and timeout skips log at warning.

### 2026-11-01 (Pedro's decisions)

(a) A cover from the manual "Gerar capa com Grok" button also becomes the
cover when it succeeds, under the same rules. (b) A generation that finishes
after completion or at final review stays a picker option: no re-render, no
re-approval. Implemented: `selecting_cover_task(wiring, run, project)` in
`carousel_cover_autoselect` (wrapper renamed `with_cover_selection`) is used
by the autostart and by `POST /cover-generations`; the log event is now
`cover_auto_select`. Note: the button lives on the publish page, which renders the
cover picker only once the artifacts are ready (`artifactsReady`, a completed
carousel), so with (b) a manual generation from the UI normally stays a
picker option, as today; only a generation started before completion (API,
or a carousel re-run after the click) is selected.

## Files Touched

- backend/src/rag_backend/domain/constants/cover_autoselect.py (new)
- backend/src/rag_backend/application/services/carousel/cover_autoselect.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_autoselect.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_autostart.py
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_generation.py
- backend/src/rag_backend/modules/editorial/public.py
- backend/src/rag_backend/api/routes/carousels/cover_generate.py
- backend/tests/unit/modules/autopilot/test_cover_autostart_editorial_ae0581.py
- backend/tests/integration/test_autopilot_cover_autostart_pg_ae0581.py
- backend/src/rag_backend/application/services/carousel/creator_asset_service.py
- backend/tests/features/autopilot_cover_autoselect_ae0590.feature (new)
- backend/tests/unit/application/test_cover_autoselect_ae0590.py (new)
- backend/tests/unit/modules/editorial/test_cover_autoselect_task_ae0590.py (new)
- backend/tests/integration/test_autopilot_cover_autoselect_pg_ae0590.py (new)
- backend/tests/integration/test_cover_generation_manual_autoselect_ae0590.py (new)

## Test Evidence

- Unit (selector, fake store): selects at the version read; waits while
  `in_progress` then selects; times out; owner cover before the job kept;
  rebound photo and cover set while running kept (`manual_choice`); already
  selected is a no-op; completed / `final_review` / failed skipped without
  waiting, and so are `rejected` / `failed` phase statuses; CAS conflict
  skipped once, logged at info, never retried; timeout logged at warning;
  write refusal passes through; no result never reads or writes.
- Unit (task + wiring): only `succeeded` runs the selection; a selection
  crash is logged; the autostart schedules the wrapped task with the
  baseline.
- Postgres integration (real autostart, generation service and runner, asset
  store, cover switch, repository; fake bridge, inline task):
  succeeded → `slide_cover` = generated asset (`ai_image`), lock version +1,
  status unchanged, `is_public` false, no render/finalize/Instagram call;
  a photo rebound while the job ran is kept; a bridge failure leaves slide 1
  and the lock version alone; a held project lock is one logged `conflict`
  skip; a rerun is `already_selected`; store refusals (unknown generation,
  project, asset; moved baseline) write nothing; an owner photo committed
  between the re-check and the locked UPDATE is kept (`manual_choice`, lock
  version unchanged; the test fails without the `hook_asset_id` guard); a
  lock version moved after the read is a `conflict` skip.
- Integration (HTTP, SQLite, real route): a manual generation on a paused
  carousel becomes `slide_cover` (`ai_image`, lock version +1, status
  unchanged, no re-render); with a cover already chosen it is kept (lock
  version unchanged); on a completed carousel it is only a picker option
  (no re-render); `PUT /hook-photo` clears a stored generated `slide_cover`
  (the test fails without the fix). The earlier test asserting a manual
  generation never selects itself was replaced.
- Backend gates green locally (hotfix fast path, each run individually with
  the Postgres `DATABASE_URL`): format, lint, lint-diff, blanket-ignore,
  strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
  inline-prompts, gherkin-refs, comments, redis-factory, autopilot-env,
  healthcheck-loopback, openapi-fresh, bandit, pip-audit, integrity,
  duplication, migrations, schema-drift, test (8124 passed, 2 skipped),
  diff-cover (100%, 0 missing lines). Every gate PASS, none skipped.
  After the review fixes: all of the above rerun individually, PASS, none
  skipped; test 8133 passed, 2 skipped; diff-cover 100%, 0 missing lines.
  The locked write's branches run after a SQLAlchemy greenlet switch, which
  the tracer does not follow, so fake-based unit tests cover them besides the
  Postgres tests.
  Python 3.11 import check OK (3.11.15). mutation: deferred to CI (hotfix
  fast path); CI must be green before merge (no `--admin`).

## QA Report

Pending.

## Blockers

None.
