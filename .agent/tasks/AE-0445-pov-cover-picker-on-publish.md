# AE-0445 — Change the slide-1 cover photo of a Ponto de Vista carousel on the publish step

Status: In Progress
Tier: T1
Priority: P1
Type: Feature
Area: Fullstack
Owner: Claude (owner request 2026-10-20)
Agent Lane: developer → qa → release
Branch: feat/ae-0445-pov-cover-picker-on-publish
Kanban Card: TBD
Created: 2026-10-20
Updated: 2026-10-20

## Goal

On the last step of a `pov` / `pov_news` carousel (`/dashboard/create/<id>/publish`) the owner
can swap slide 1's photo for another photo of their library (or the run's GrokBot cover offer),
and the slides + PDFs re-render with the new photo.

## Problem

Owner request 2026-10-20. Prod project `787085ba-c127-4d3a-9d90-020da2d605a3` (autopilot run
`d18de18a`, `awaiting_owner`; read-only check: `status=completed`, `phase_status=awaiting_human`,
`content_mode=pov`, `hook_asset_id=38421503…`, `slide_cover=null`, `lock_version=10`). The slide-1
photo is chosen once at create time (wizard photo step, or the autopilot rotation) and there is no
way to change it afterwards: the only post-completion cover switch is the AE-0418 Telegram tap,
and only for a GrokBot cover offer.

## Scope

- Backend: `GET /api/carousels/{id}/cover-options` (the owner's `hook` library photos with a
  stored file, plus the autopilot run's GrokBot cover offer when there is one, and the current
  slide-1 asset) and `PUT /api/carousels/{id}/cover` (`{asset_id, expected_version}`), owner or
  admin only (editor auth). Completed POV carousel without an active run only.
  - library photo → `hook_asset_id` = the photo, `slide_cover` cleared (the default POV slide 1);
  - GrokBot offer → `slide_cover` = the offer (AE-0418 semantics);
  - staged before anything is written, then the lock-version CAS + write under the project lock,
    then the AE-0313 republish (slides + PDFs, both locales, hero images reused). Reuses
    `SlideCoverSwitchService` (extended with an optional hook photo).
  - 409 `version_conflict` on a moved lock version / held lock, 409 `resume_already_in_progress`
    while a run is active, 422 for a non-POV mode, a non-completed project, or an asset that is
    not one of the options (foreign owner, other role, file gone); 422 with the render errors
    when the re-render fails (the choice stays stored; "Rebuild PDF" retries).
- Frontend: publish page "Capa (slide 1)" section for `pov` / `pov_news`: current photo marked,
  thumbnails as a keyboard-accessible radiogroup, progress while the republish runs, slide
  previews/PDF cache-busted with the new artifact version, visible errors (409 → reload hint).
  pt + en copy.

## Non-Goals

- No change for `news_analysis` carousels (the picker is not shown; the API refuses).
- No upload from the publish page (the library upload lives on the create wizard).
- No new Telegram notice: the web switch does not resend the Telegram review album (no resend
  path exists for an out-of-band change; see "Autopilot" below).

## Decisions

- Body field `expected_version` instead of an `If-Match` header: every lock-version CAS in the
  carousel API (`/workflow/resume`) takes it in the body; the publish page already holds
  `workflow.lock_version`.
- Choosing a library photo clears `slide_cover` (otherwise a GrokBot cover chosen on Telegram
  would keep hiding the newly chosen photo).
- Autopilot: the run stays `awaiting_owner`. Telegram approve reads the current lock version
  (`FinalReviewApproval.approve`), so the bumped version does not break it, and Instagram publish
  reads the current public slide URLs (`PublishingCarouselSource`), so the published media is the
  re-rendered deck. The Telegram review message already sent still shows the old slide 1; no fresh
  notice is sent (no resend path for a web-side change exists, and the brief forbids inventing one).

## Acceptance Criteria

- [ ] AC1 `GET cover-options` lists the owner's library photos (role `hook`, file present) and the
      run's GrokBot offer, marks the current slide-1 asset, and is refused for a non-POV carousel.
- [ ] AC2 `PUT cover` with a library photo binds it as the slide-1 photo, clears `slide_cover`,
      bumps the lock version and re-renders through the republish path.
- [ ] AC3 `PUT cover` with the GrokBot offer stores it as `slide_cover` and re-renders.
- [ ] AC4 409 on a stale `expected_version` / held lock / active run; nothing written.
- [ ] AC5 422 for non-POV, non-completed, a foreign or unknown asset, or a photo whose file is gone.
- [ ] AC6 Publish page shows "Capa (slide 1)" only for `pov` / `pov_news`, current photo marked,
      keyboard accessible, progress while switching, previews refreshed, errors visible (409 hint).
- [ ] AC7 pt + en copy; gates green.

## Gherkin

- `backend/tests/features/carousel_cover_pick_ae0445.feature`
- `frontend/tests/features/publish-cover-picker-ae0445.feature`

## Affected Areas

- [x] Backend
- [x] Frontend
- [x] Tests

## Dependencies

AE-0418 (slide cover switch), AE-0313 (republish), AE-0376 (photo library).

## Progress Log

### 2026-10-20

Ticket created from the orchestrator brief; plan above.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
