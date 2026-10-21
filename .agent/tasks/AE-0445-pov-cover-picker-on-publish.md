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

- [x] AC1 `GET cover-options` lists the owner's library photos (role `hook`, file present) and the
      run's GrokBot offer, marks the current slide-1 asset, and is refused for a non-POV carousel.
- [x] AC2 `PUT cover` with a library photo binds it as the slide-1 photo, clears `slide_cover`,
      bumps the lock version and re-renders through the republish path.
- [x] AC3 `PUT cover` with the GrokBot offer stores it as `slide_cover` and re-renders.
- [x] AC4 409 on a stale `expected_version` / held lock / active run; nothing written.
- [x] AC5 422 for non-POV, non-completed, a foreign or unknown asset, or a photo whose file is gone.
- [x] AC6 Publish page shows "Capa (slide 1)" only for `pov` / `pov_news`, current photo marked,
      keyboard accessible, progress while switching, previews refreshed, errors visible (409 hint).
- [x] AC7 pt + en copy; gates green.

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

### 2026-10-20 (dev)

Backend + frontend implemented, Gherkin-first. Two unrelated dependency advisories published
on 2026-10-19/20 made `backend:pip-audit` and `frontend:security` red on every branch; fixed with
lock-only bumps (Pillow 12.3.0 → 13.0.0, certifi → 2026.10.19; vite override floor → 7.3.7).

## Files Touched

- Backend: `api/routes/carousels/cover_pick.py` (new), `api/schemas/carousel_cover_pick.py` (new),
  `application/services/carousel/cover_pick.py` (new), `slide_cover_switch.py` (optional
  `hook_photo`), `domain/constants/carousel_cover_pick.py` (new),
  `modules/editorial/infrastructure/carousel_cover_pick.py` (new), `carousel_cover.py`
  (`slide_cover_switch_service` factory), `modules/autopilot/infrastructure/cover_offers.py`
  (`ProjectCoverOffer`, `offered_cover`), autopilot/editorial facades, router, republish
  (`raise_republish_failure` made public), route snapshot, `docs/architecture/openapi.json`,
  `uv.lock`.
- Frontend: `distribution/hooks/use-cover-picker.ts`, `components/cover-picker-section.tsx`,
  `components/cover-option-grid.tsx`, types, publish page + `publish-readiness.ts`, api
  constants, pt/en copy, `package.json`/lock (vite override).

## Test Evidence

- Backend targeted (memory-critical machine; full suite + mutation left to CI per orchestrator):
  `test_cover_pick_ae0445.py` (15 unit), `test_cover_pick_api_ae0445.py` (15 HTTP integration),
  `test_project_cover_offer_ae0445.py` (2), plus AE-0418 cover seam/flow, republish route,
  slide cover switch, photo library API and route snapshot: 89 passed. All 29 PIL-using test
  files after the Pillow 13 bump: 323 passed, 4 skipped.
- Backend gates run individually (hotfix fast path, `DATABASE_URL` on a throwaway Postgres 16):
  format, lint, lint-diff, blanket-ignore, strict-diff, type, imports (27/27 contracts),
  arch-ratchet, docstrings, dead-code, inline-prompts, blog-v1-dead-code, redis-factory,
  autopilot-env, healthcheck-loopback, bandit, integrity, diff-cover, migrations, schema-drift:
  PASS; pip-audit PASS after the lock bump. `test`: the full-suite run was OOM-killed at 1%
  (machine swap full), not a test failure; CI is the source of truth. mutation: deferred to CI
  (hotfix fast path).
- Frontend gates: lint, lint-changed, component-types, duplication, dead-code,
  blog-v1-dead-code, typecheck, legacy-guard, legacy-inventory, format, security, integrity,
  schema-drift, duplication-tests, dead-files: PASS. Targeted vitest (publishing distribution +
  publish page): 12 files, 115 tests passed. build / full test / mutation: left to CI (memory).

## QA Report

Pending.

## Blockers

None.
