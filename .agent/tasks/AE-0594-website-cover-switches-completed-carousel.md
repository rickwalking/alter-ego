# AE-0594 — A website cover switches a completed carousel and reopens final review

Status: Blocked
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

## Open questions (for Pedro)

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

## Acceptance Criteria

To be fixed once the open questions are answered. Planned scenarios: happy
path, a manual choice wins, a lock conflict is skipped, a failed generation,
a scheduled carousel does not publish until re-approved, an already published
carousel, an idempotent replay, an autopilot cover on a completed carousel
unchanged.

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

## Files Touched

- .agent/tasks/AE-0594-website-cover-switches-completed-carousel.md (new)

## Test Evidence

None yet (no code).

## QA Report

Pending.

## Blockers

Open questions 1 to 3 above (Pedro).
