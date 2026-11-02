# AE-0594 — A website cover switches a completed carousel and reopens final review

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Branch: feat/ae-0594-website-cover-on-completed
Created: 2026-11-02
Updated: 2026-11-02

## Goal

Pedro's decision (2026-11-02): a cover generated from the website ("Gerar
capa com Grok", `POST /carousels/{id}/cover-generations`) on a carousel that
is already completed switches slide 1 when the generation succeeds. The
carousel is re-rendered and goes back to final review, so the owner has to
approve it again before anything goes out. It never publishes, never touches
`is_public`/release, and never bypasses the owner's approval. A cover the
owner picked by hand while the job ran still wins; a lock-version conflict is
a logged skip; a failed or refused generation leaves the cover alone; a
replayed success changes nothing.

Out of scope: autopilot-started covers on completed carousels (they stay a
picker option) and carousels that are not completed (AE-0590).

## Problem

AE-0590 skips the selection on a completed carousel or one at final review
(`REASON_AUTO_SELECT_COMPLETED`), so the website generation only shows up as
a picker option. The publish page only shows the Grok button once the
artifacts are ready, so in practice a website generation never becomes the
cover on its own.

## Findings (step 1, read before coding)

### How a completed carousel's review and approval are stored

There are three layers, and every publish path checks the editorial one:

1. **Editorial row and checkpoint.** A completed carousel waiting for review
   has `status = completed`, `current_phase = final_review`,
   `phase_status = awaiting_human`, `workflow_status = draft`. The LangGraph
   thread waits at the `final_review` interrupt. On approve,
   `final_review_phase` sets `workflow_status = approved_for_publish` and
   `quality_passed = true`, and the graph parks at the internal
   `approved_hold` node (`phase_status = approved`). `get_state` keeps
   reporting `final_review / approved` while it is parked there.
2. **Publish guards.** All of these require
   `workflow_status == approved_for_publish`: the website release
   `POST /carousels/{id}/publish` (`crud.py`, sets `is_public`), the website
   Instagram publish (`publishing.py`), the autopilot publish gate
   (`domain/publish.py::_workflow_reason`), and the scheduled sweep
   (`scheduled_publish.py::_still_approved`; a run that is no longer approved
   at its time moves `scheduled -> expired`, reason `schedule_withdrawn`, and
   nothing is published). The blog `ScheduledPublishService` handles blog
   posts only, never carousels.
3. **Autopilot run (Telegram), only for autopilot carousels.** The review is
   `awaiting_owner`, and an approved run waiting for its time is `scheduled`.
   Telegram callbacks carry only the run id, not a revision.
   `FinalReviewApproval.approve` resumes at the current `lock_version`, and
   it skips the editorial approve when the carousel is already
   `approved_for_publish` (the "schedule cancelled" case). `Publicar agora` on
   a `scheduled` run releases and publishes straight away
   (`_publish_scheduled`), without a new editorial approve.

### What the existing switch and republish do

`CoverPickService.pick` / `SlideCoverSwitchService.switch` (CAS under the
project lock, then `RepublishRenderer` → `republish_completed_carousel` →
`finalize_carousel_after_images_approval` → `export_and_complete_carousel`)
re-render and bump `lock_version`. They never change
`phase_status`/`workflow_status` and never touch the graph. A switch on an
approved or scheduled carousel therefore stays approved. That is fine for an
owner pick, but not for an automatic switch.

### What "back to final review" must set

- **(a) The owner is asked again.**
  - Website: the review UI follows `final_review / awaiting_human`.
  - Telegram (autopilot carousels): the run has to go through the
    "final-review stop" again, which moves it to `awaiting_owner` and sends a
    fresh ready notice at the new `lock_version`. The existing path is the
    "Usar capa do Grok" review rework: `awaiting_owner -> reworking` plus a
    queued `owner_cover` intent. The worker's `ReworkStep._cover` runs
    `SlideCoverSwitchService`, and the normal stop re-notifies. That rework
    switches to the run's GrokBot offer (`covers.chosen_cover(run)`), not to
    a generated asset, and it lives in the autopilot module, which editorial
    must not import.
- **(b) A previous approval cannot approve the new render.**
  - Website: already holds. The review resume takes a `lock_version` CAS
    (`bump_resume_lock_version`), and the switch bumps the version.
  - Telegram: does **not** hold today. An old review message's Approve
    (run id only) acts on any `awaiting_owner` run at the current version.
    The run therefore has to leave `awaiting_owner` (or `scheduled`) before
    the re-render and come back with a fresh notice.
- **(c) A `scheduled` or approved carousel does not publish until it is
  re-approved.** The only flag every publish path honours is
  `workflow_status`. It would have to go back to `draft` (with
  `quality_passed = false`), and the graph would have to wait at the
  `final_review` interrupt again, so that a new approve restores
  `approved_for_publish`. **The current model cannot do this cleanly:**
  - `approved_hold` routes only to END or to a full re-run of research,
    outline, content, design or images (`route_after_hold`,
    `FINAL_REVIEW_SEND_BACK_PHASES`). There is no edge back to the
    `final_review` interrupt. A send-back to `images` would regenerate every
    image (cost, and it throws away what the owner approved).
  - Patching the parked checkpoint (`patch_parked_checkpoint`) to
    `awaiting_human` / `draft` would show a review, but an approve then
    resumes `approved_hold`. That only sets `phase_status = approved` and
    goes to END, without restoring `approved_for_publish`, so the carousel
    could never be published again.
  - Moving only the autopilot run back (`scheduled -> awaiting_owner`, which
    exists as "cancel") keeps `approved_for_publish`. The website publish
    and Instagram buttons, and the old message's `Publicar agora`, would
    then still publish the unreviewed render.
  - None of this needs a schema change, but each option is a new workflow
    design (a graph edge or a new resume action), so step 1 stops here as
    instructed.
- **An already published carousel** (autopilot `published`/`publishing`, or
  released `is_public = true` / posted from the website) must keep the new
  cover as a picker option only. A re-render would change the live public
  slides and PDF that the release serves, which would publish an image the
  owner never approved. Nothing in the existing code argues otherwise.

### Clean sub-case

A completed carousel that is **not yet approved** (editorial
`final_review / awaiting_human`, `workflow_status = draft`) needs no graph
change: the switch plus re-render keep it at final review, and the website
CAS covers (b). For an autopilot carousel at `awaiting_owner`, (b) still
needs the run moved out of `awaiting_owner` and a fresh notice, either by
reusing the review rework with a "generated cover" target or by an autopilot
facade that the API route calls.

## Pedro's decision (2026-11-02)

Answers to the three questions below:

1. **Scope of this ticket is the clean case** (option B for now): a website
   cover that succeeds on a completed carousel still waiting for its first
   approval (`final_review / awaiting_human`, `workflow_status` draft)
   switches slide 1, re-renders through the existing switch/republish
   services, and stays in final review. Reopening the review of an approved or
   scheduled carousel (option A) is the next ticket (AE-0597); this one only
   keeps the guard easy to lift.
2. **The guard ships here** (a real bug): `PUT /carousels/{id}/cover` on an
   approved carousel (`approved_for_publish`, autopilot scheduled ones
   included) today re-renders it and leaves it publishable with an image the
   owner never saw. Until AE-0597 the picker refuses approved, scheduled and
   published carousels with the coded error `cover_switch_requires_review`
   (pt/en message on the publish page), and the website auto-switch skips
   them (logged); the generated cover stays a picker option. Published
   carousels never switch and never re-render.
3. **Wiring:** the API layer composes the Telegram hook, the same pattern as
   `selecting_cover_task`; editorial never imports autopilot. On Telegram the
   run leaves `awaiting_owner` and the review is sent again at the new lock
   version, so the old message cannot approve the new render.

## Open questions (answered above, kept for the record)

1. **Approved or scheduled carousels:** how should approval be revoked
   without re-running a phase? Options:
   - (A) add an `approved_hold -> final_review` route for a new "reopen
     review" resume, which drops `approved_for_publish`, waits at the
     interrupt, and lets a later approve restore it;
   - (B) leave approved and scheduled carousels alone, so the cover stays a
     picker option (the same as published), and switch only carousels still
     waiting for their first approval;
   - (C) something else.
2. For an autopilot carousel that is `scheduled` when the cover lands:
   should the run move back to `awaiting_owner` (keeping the planned time
   for a re-approve) or expire?
3. To tell Telegram, the website-triggered path has to cross from editorial
   into autopilot. Is it OK for the API route to compose an autopilot hook
   (as `selecting_cover_task` composes editorial today), or should this be
   an event that the autopilot worker consumes?

## Non-Goals

- No auto-publish, no release, no `is_public` change.
- No change for autopilot-started covers on completed carousels.
- No change for carousels that are not completed (AE-0590).

## Scope (design)

- **Guard** (`application/services/carousel/cover_switch_guard.py`):
  `cover_switch_refusal(project, workflow_status)` returns
  `carousel_published` when `is_public` and `carousel_approved` when
  `workflow_status == approved_for_publish`. Every Instagram post needs the
  approval, which nothing drops afterwards, so "approved" covers scheduled and
  posted carousels; "released" is the public one. This is the single place
  AE-0597 lifts for approved carousels.
- **Picker** (`CoverPickService.pick`): reads `workflow_status` through
  `EditorialReviewState` (the legacy ACL) and raises
  `CoverPickError(cover_switch_requires_review)` (HTTP 422) before any stage,
  write or render. The lock-version CAS covers an approval that lands after
  the read (the resume CAS bumps the version).
- **Website auto-switch** (`reviewing_cover_task`, the route only): the
  AE-0590 selection with a `review` switch. A non-completed carousel keeps the
  AE-0590 gate write unchanged. A completed carousel goes to
  `switch_in_review`:
  1. refusals, each a logged skip: approved / published (the guard); not at
     `final_review / awaiting_human` (`not_in_final_review`); a failed or
     rejected phase; already the cover (`already_selected`, idempotent); any
     change to `slide_cover` / `hook_asset_id` since the request's baseline
     (`manual_choice`). A cover chosen before the click does not block: the
     owner asked for a new cover on a finished carousel.
  2. hold the Telegram review (`ReviewHold`, composed by the API layer from
     `modules.autopilot.cover_review_hold`): an autopilot run in
     `awaiting_owner` moves to `reworking` with a `website_cover` rework queued
     (CAS); any other state (scheduled, published, none) is not held.
  3. `EditorialReviewCoverStore`: fresh session, re-check, stage, then under
     the project lock and the unchanged lock-version CAS a `SELECT ... FOR
     UPDATE` re-check (guard, phase, baseline) and the write of `slide_cover`
     alone; a refusal rolls the CAS bump back. Then the republish renderer the
     picker's switch uses (`RepublishRenderer`); on success the
     needs-republish marker is cleared. The workflow, its approval, `is_public`
     and the release are never written. A held lock or a moved version is
     `conflict`, never retried.
  4. release: `changed` (the write landed) clears the rework and leaves the run
     in `reworking`; the worker's normal final-review stop moves it back to
     `awaiting_owner` and sends the review at the new lock version. Unchanged
     (refusal, conflict) moves it straight back to `awaiting_owner` (reason
     `website_cover_kept`), no new message. A crash releases as changed (a new
     review at the current version is always safe).
- **Worker** (`ReworkStep`): a `website_cover` rework waits (tick returns 0)
  until released; a hold older than 15 minutes (a restart killed the task) is
  escalated (see below), never re-sent.
- **Telegram taps are bound to their revision** (`PublishChoiceActions`,
  `FinalReviewApproval`, `review_revision_guard`): every review keyboard and
  every reminder message is recorded per revision in the notice ledger (the
  JSON `telegram_message_ids` column, no schema change). Approve, publish now
  and the schedule buttons on an `awaiting_owner` run resolve the tapped
  message's revision; an unknown message or a revision that is not the
  carousel's current lock version changes nothing. The answer is accurate: a
  newer review is in the chat ("use a mensagem de revisão mais recente"); no
  review was sent yet for the current version, so the run goes `awaiting_owner
  -> reworking` (`review_outdated`, its 72-hour anchor kept) and the worker
  sends it ("chega numa nova mensagem"); or the current review's delivery is
  exhausted, so the owner is pointed at the dashboard (no bounce). The editorial
  approve runs its CAS at the tapped revision, never at the version read now.
  A typed time ("Outro horário") answers the revision of the message where
  "Outro horário" was tapped: that revision is stored with the pending reply
  (JSON ledger) and the approve CASes at it; a hold or a newly recorded review
  drops an open time reply. A refused typed time gets text only (no buttons on
  an unrecorded message). An already approved carousel (a cancelled schedule)
  needs no approve and is not checked: its slide 1 cannot change.
- **Hold bookkeeping:** the hold keeps the run's `updated_at` (the 72-hour
  review window) and stores its start time in the queued rework's feedback;
  an unchanged release restores `awaiting_owner` with the same anchor. The
  runner skips a run with an active hold and steps the next active run.
- **Invariant: no approval between the cover write and a settled render
  (mechanism, third review):** the locked write stamps the existing
  `needs_republish_since` marker in the same commit as `slide_cover`. Both
  approve paths refuse an approve while the marker is set: the website resume
  route (`ensure_rendered_before_approve`, typed 409 `build_in_progress`) and
  the run-owned path the Telegram approve uses (`run_automation_phase`,
  `resume_already_in_progress`). The CAS makes it atomic: an approve whose
  version predates the write loses its CAS, one read after it sees the marker.
  Only a settled render clears the marker (the switch's own render, the
  rollback's re-render, or the republish sweep), so a crash, a deploy
  cancelling the task, or a failed rollback leaves approval refused until the
  sweep renders the carousel, and the held Telegram run is escalated by the
  worker (hold expiry), never released to approval. The marker also covers a
  slide-text edit not yet republished: an approve then waits for its render
  (a few minutes at most, the sweep's guarantee).
- **Render under the build lock, review re-checked:** the switch renders
  through the republish pipeline inside `republish_build_lock`, re-checking
  `review_refusal` first, so a render never lands on an approved or released
  carousel. Any render failure (every exception type) rolls the cover back:
  the restore waits for the lock (30 x 4 s), compares the whole slide-1 value
  (an owner's later value is kept), and the restored cover is **always**
  rendered again; a restore that never gets the lock or a re-render that fails
  is `rollback_failed` (logged as an error, marker kept, held run escalated
  with `website_cover_unsafe`). Cancellation is never swallowed; it leaves the
  hold and the marker, both recoverable as above.
- **Defense in depth at every render:** each artifact build records the cover
  slide 1 was rendered with (`slide_one_cover` in the artifact manifest JSON
  file: the `slide_cover` asset id, else the bound photo; no database schema
  change). The shared finalize step (`export_and_complete_carousel`, used by
  the republish service, the sweep, a slide edit's republish, a manual
  republish and the switch) refuses to render an approved or released
  carousel whose current cover differs from the one the active version
  recorded (`cover_change_requires_review`); the carousel keeps its artifacts.
  An active version built before this change has no record and there is no
  other stored trace of the cover a render used, so such a version is not
  compared (the switch never writes to approved carousels and approval is
  refused while a switch's render is pending, which closes that gap).
- **Notice ledger writes are serialized:** every writer passes the ledger it
  read (`SaveNoticeLog.base`); `SqlNoticeLogStore.save` reads the row
  `FOR UPDATE` and applies only that writer's change (three-way merge), so a
  stale writer never erases a recorded review or reminder.
- **Telegram GrokBot cover tap refused by the guard** maps to
  `CoverSwitchStatus.REQUIRES_REVIEW` (`cover_requires_review`), not "file
  missing".
- **Telegram "Corrigir" on an approved carousel:** checked, already safe. The
  tap needs the run in `awaiting_owner`, and the queued fix only runs while the
  editorial is at `final_review / awaiting_human`; an approved carousel is at
  `approved`, so the rework is dropped and nothing is repaired.
- **Picker guard under the lock:** `SlideCoverSwitchService` re-reads the
  approval and release (`EditorialReviewState`, a direct column select, never
  the cached row) after the CAS under the project lock; an approved or
  published carousel rolls the CAS back and answers
  `cover_switch_requires_review`. The route answers it as **409** (a state
  conflict).
- **Telegram "Usar capa do Grok" at review** (the other
  `SlideCoverSwitchService.switch` caller, via `ReworkStep._cover`): only
  runs while the editorial is at `final_review / awaiting_human` and the run
  is `awaiting_owner`, so it never re-renders an approved or scheduled
  carousel. Left unchanged.
- **Frontend:** the cover picker maps the 422 detail
  `cover_switch_requires_review` to `publish.coverPicker.requiresReview`
  (pt/en).

## Acceptance Criteria

- [x] A website cover on a completed carousel in final review (draft) becomes
      slide 1 (`ai_image`), the slides are re-rendered, and the carousel stays
      `completed / final_review / awaiting_human / draft`, `is_public` false;
      no Instagram call.
- [x] A website approval read before the switch is refused by the resume CAS.
- [x] Telegram: the run leaves `awaiting_owner` before the write and render;
      the worker sends the review again at the new lock version; approve,
      publish and schedule from an older review message are refused.
- [x] A manual choice while the job ran wins (before the hold and under the
      lock); a lock conflict is a logged skip; a failed generation changes
      nothing; a replay is `already_selected`.
- [x] The picker refuses approved, scheduled and published carousels with
      `cover_switch_requires_review`; nothing is staged, written or rendered;
      the publish page explains it (pt/en).
- [x] The website auto-switch skips approved/scheduled (`carousel_approved`)
      and published (`carousel_published`) carousels; the cover stays a picker
      option; a scheduled run is not touched.
- [x] An autopilot-started cover on a completed carousel is unchanged
      (`carousel_completed`).
- [x] Gates green (every backend gate except local mutation, individually,
      with the Postgres `DATABASE_URL`; frontend scope; Python 3.11 import
      check).

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

AE-0590 (generated cover selection), AE-0581 (autopilot auto-cover).

## Progress Log

### 2026-11-02

Ticket created from Pedro's decision (2026-11-02). Step 1 findings recorded
above. Blocked on the open questions: the current workflow cannot revoke a
final-review approval cleanly (no `approved_hold -> final_review` path), and
Telegram approvals are not tied to a revision. No production code changed.

Pedro answered (2026-11-02, recorded above): clean case + guard here, reopen
review in AE-0597, API-layer wiring. Unblocked and implemented as described
in "Scope (design)".

### 2026-11-02 (independent review fixes)

Merged origin/main (AE-0588). Blocker B1 fixed by binding Telegram approve,
publish and schedule to the tapped message's revision (reviews and reminders
recorded per revision; no schema change). S1/S3: needs-republish stamped with
the cover; rollback after a failed or overtaken render. S2: the runner skips a
held run. S4: guard re-checked under the lock; 409 for the refusal. S5:
Postgres tests through the real approve route, the publish-now vs hold race,
the locked picker refusal and the rollbacks. Nits: test files split under 400
lines, `NoReviewHold` moved to the test fakes, typed test helpers, the
frontend test scenario fixed, the unchanged release keeps the 72-hour
anchor. Existing approve/schedule test fixtures now tap a recorded review
(message 9 at revision 4), as a real tap does.

### 2026-11-02 (third review: invariant at the approval and render points)

Approval refused while the needs-republish marker is set (website route and
the Telegram approve path), the marker stamped with the cover and cleared only
by a settled render; the switch renders under the build lock with the review
re-checked; the rollback always re-renders the restored cover and reports
`rollback_failed` when that fails; every artifact build records slide 1's
cover and every render of an approved or public carousel refuses a different
one; cancellation leaves a recoverable state; clearer unsafe-state text. Merge
nits: a pending change applies only when nobody changed it meanwhile, attempt
counts merge as increments.

### 2026-11-02 (second review fixes)

B1: the typed time answers the tapped revision (stored with the pending
reply), dropped on a hold or a new review. B2: catch-all render errors, a
bounded waiting restore with its real result, escalation on a failed rollback
or an outlived hold, no needs-republish marker, whole-value rollback compare.
Should-fixes: serialized ledger writes (row lock + three-way merge), a test of
the approve CAS at the tapped revision, no bounce for an exhausted review and
no window reset, accurate refusal texts and no unrecorded keyboards, the
GrokBot cover refusal reason, typed command objects instead of tuples.

## Files Touched

- backend/src/rag_backend/domain/constants/cover_review_switch.py (new)
- backend/src/rag_backend/application/services/carousel/cover_switch_guard.py (new)
- backend/src/rag_backend/application/services/carousel/cover_review_switch.py (new)
- backend/src/rag_backend/application/services/carousel/cover_autoselect.py
- backend/src/rag_backend/application/services/carousel/cover_pick.py
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_review_switch.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_autoselect.py
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_pick.py
- backend/src/rag_backend/modules/editorial/public.py
- backend/src/rag_backend/modules/autopilot/application/cover_review_hold.py (new)
- backend/src/rag_backend/modules/autopilot/infrastructure/cover_review_hold.py (new)
- backend/src/rag_backend/modules/autopilot/domain/review_revision.py (new)
- backend/src/rag_backend/modules/autopilot/domain/cover_hold.py (new)
- backend/src/rag_backend/modules/autopilot/application/review_revision_guard.py (new)
- backend/src/rag_backend/modules/autopilot/application/owner_approval.py
- backend/src/rag_backend/modules/autopilot/application/schedule_steps.py
- backend/src/rag_backend/modules/autopilot/domain/notice_log.py
- backend/src/rag_backend/modules/autopilot/domain/models.py
- backend/src/rag_backend/modules/autopilot/infrastructure/repository.py
- backend/src/rag_backend/modules/autopilot/notify_constants.py
- backend/src/rag_backend/modules/autopilot/constants.py
- backend/src/rag_backend/modules/editorial/infrastructure/cover_review_rollback.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/cover_review_state.py (new)
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover.py
- backend/src/rag_backend/application/services/carousel/slide_cover_switch.py
- backend/src/rag_backend/api/routes/carousels/cover_pick.py
- backend/tests/integration/test_website_cover_review_guard_pg_ae0594.py (new)
- backend/tests/integration/test_website_cover_review_route_pg_ae0594.py (new)
- backend/tests/unit/application/cover_review_fakes.py (new)
- backend/tests/unit/application/test_cover_switch_guard_ae0594.py (new)
- backend/tests/unit/modules/autopilot/test_review_revision_ae0594.py (new)
- backend/tests/unit/modules/autopilot/test_owner_actions.py
- backend/tests/unit/modules/autopilot/test_schedule_webhook_ae0370.py
- backend/src/rag_backend/modules/autopilot/application/rework_step.py
- backend/src/rag_backend/modules/autopilot/application/runner.py
- backend/src/rag_backend/modules/autopilot/application/publish_choice.py
- backend/src/rag_backend/modules/autopilot/cover_constants.py
- backend/src/rag_backend/modules/autopilot/public.py
- backend/src/rag_backend/modules/autopilot/__init__.py
- backend/src/rag_backend/api/routes/carousels/cover_generate.py
- backend/tests/features/website_cover_review_switch_ae0594.feature (new)
- backend/tests/integration/website_cover_review_pg_support.py (new)
- backend/tests/integration/test_website_cover_review_switch_pg_ae0594.py (new)
- backend/tests/integration/test_cover_pick_review_guard_pg_ae0594.py (new)
- backend/tests/integration/test_cover_pick_review_guard_api_ae0594.py (new)
- backend/tests/unit/application/test_cover_review_switch_ae0594.py (new)
- backend/tests/unit/modules/autopilot/test_cover_review_hold_ae0594.py (new)
- backend/tests/unit/application/test_cover_pick_ae0445.py
- backend/tests/unit/application/test_cover_generation_parts_ae0508.py
- frontend/src/modules/publishing/distribution/constants.ts
- frontend/src/modules/publishing/distribution/components/cover-picker-section.tsx
- frontend/src/modules/publishing/distribution/components/cover-picker-section.test.tsx
- frontend/src/i18n/locales/en.json
- frontend/src/i18n/locales/pt.json

## Test Evidence

Review-fix round (2026-11-02): B1 unit tests (old review before and after the
new one is logged, old reminder, unknown message, current reminder publishes at
its revision, approve-after-rework from the newest review, slot on current and
old review, typed time for an outdated review, ledger round-trip); hold anchor,
skip of a held run, outlived and undated holds; Postgres: approve route answers
409 for the pre-switch version and 202 for the current one, publish-now vs
hold race (exactly one wins; a published run makes the switch skip as
approved), approval landing before the picker's locked write refused, failed
render rolled back (cover restored, marker cleared, review re-sent), approval
before the render rolled back and rendered again, a dying process leaves the
marker, the unchanged release keeps the run's `updated_at`.

- Postgres (real generation, selection, review store with lock + CAS +
  `FOR UPDATE`, run repository and review hold; fake bridge, recorded render):
  clean switch stays in final review (draft, not public, lock +1, one render,
  no Instagram); a stale website approval at the old version raises the
  version conflict; the run is `reworking` with the `website_cover` rework
  during the render and `reworking` without it after; an owner photo
  committed between the re-check and the locked write is kept and the run is
  handed back (`website_cover_kept`); a change before the read is
  `manual_choice` with no hold; a held lock is `conflict` and the run is
  handed back; a failed generation changes nothing; a replay is
  `already_selected` with no second render; approved and scheduled carousels
  are skipped (`carousel_approved`, the scheduled run untouched, the cover
  listed as a generated option); a released one is `carousel_published`; an
  autopilot-started cover stays `carousel_completed`. Picker: approved,
  scheduled and published refused with `cover_switch_requires_review`,
  nothing written or rendered; a draft carousel in review still switches.
- HTTP (SQLite): `PUT /cover` answers 422 `cover_switch_requires_review` for
  approved, approved + public and public; a draft one switches (200);
  `POST /cover-generations` on a completed carousel in final review switches
  slide 1 and renders once (route wiring).
- Unit: the review-switch rules over fakes (hold/release pairing, conflict
  releases unchanged, a crash releases as changed, render failure logged at
  warning, every refusal neither holds nor writes, a cover chosen before the
  job does not block, replay, no review switch keeps `carousel_completed`, a
  non-completed carousel keeps the gate write); the guard; the picker refuses
  before switching. Autopilot: the hold's CAS and states, both releases; the
  worker waits on a fresh hold, re-sends after release at revision 4, drops
  an outlived or undated hold; approve / publish now / schedule from an older
  review message are refused, the newest still publishes.
- Frontend: the picker shows the requires-review message for the coded 422
  and the generic failure for a non-API error.
- The tests fail without the change: with the guard, the replaced-review check
  and the locked re-check neutralised, 19 of the new tests fail; the
  website-switch tests need `reviewing_cover_task`, which does not exist
  before.

## QA Report

Pending.

## Blockers

None (Pedro answered 2026-11-02).
