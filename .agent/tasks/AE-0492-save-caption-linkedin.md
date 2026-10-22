# AE-0492 — Save the Instagram caption and LinkedIn post (PT/EN) edits

Status: Review
Tier: T2
Priority: High
Type: Bug
Area: Backend + Frontend
Owner: Pedro Marins
Branch: fix/ae-0492-save-caption-linkedin
Created: 2026-10-22
Updated: 2026-10-22

## Goal

Edits to the Instagram caption and the LinkedIn post (PT and EN) on the publish page are saved on the
server, survive a reload, and are the texts that get copied and published.

## Problem

Dashboard QA (DQ-D-12, DQ-D-13): on `/dashboard/create/{id}/publish` the caption and LinkedIn textareas
accept edits, but `publish-panel.tsx` keeps them in React state only. A reload brings back the generated
text, "Copiar post" copies whatever is on screen, and "Publicar no Instagram" sends the unsaved
client-side text. The storage exists (the canonical `blog_posts.distribution` home of ADR-011, mirrored to
the `carousel_projects.caption` / `linkedin_post_pt` / `linkedin_post_en` columns); only the write route
and the UI save are missing.

## Scope (Pedro, 2026-10-22: persist through the backend with lock_version / If-Match, no schema change)

- `PATCH /api/carousels/{id}/copy` with `If-Match: <lock_version>` saves any of `caption`,
  `linkedin_post_pt`, `linkedin_post_en` through the carousel repository (the ADR-011 dual-write), takes
  the `lock_version` compare-and-swap and returns the saved texts plus the new `lock_version`.
- Owner or admin only (403 otherwise); 428 without `If-Match`; 409 `version_conflict` on a stale lock,
  409 `resume_already_in_progress` while a workflow run is active, 409 `caption_published` when the
  caption of a carousel already published on Instagram is changed; 422 on an empty body or texts over the
  platform limits (caption 2,200, LinkedIn 3,000 characters).
- Publish page: explicit "Salvar" with a visible saved / unsaved / error state for each text; "Copiar" and
  "Publicar no Instagram" are disabled while the text has unsaved edits, so they always use the saved
  text; leaving the page through an in-app link with unsaved edits asks first in a styled dialog (closing
  the tab keeps the browser's own prompt).

## Non-Goals

- Editing in "Revisão final", `caption_en`, the blog body (AE-0505).
- Version history of the texts (AE-0506).
- Changing what happens to the approval when the text is edited (Q8, AE-0505).

## Acceptance Criteria

- [x] Given the publish page of an unpublished carousel, When the owner edits the Instagram caption and
      clicks Save, Then `PATCH /api/carousels/{id}/copy` persists `caption` and a reload shows the edit.
- [x] Given the LinkedIn tab, When the owner edits the PT or EN post and saves, Then `linkedin_post_pt` /
      `linkedin_post_en` persist and survive reload; "Copiar post" copies the saved text.
- [x] Given unsaved edits, When the owner follows an in-app link, Then a styled dialog (not
      `window.confirm`) asks before leaving.
- [x] Given "Publicar no Instagram", Then the published caption is the saved caption (publish is disabled
      while the caption has unsaved edits).
- [x] Given a non-owner non-admin, Then the PATCH returns 403; given a carousel published on Instagram,
      Then a caption change returns 409.
- [x] Given a stale `If-Match`, Then the PATCH returns 409 `version_conflict` and nothing is saved; without
      `If-Match` it returns 428.

## Gherkin Scenarios

See `backend/tests/features/carousel_copy_edit_ae0492.feature` and
`frontend/tests/features/publish-copy-save-ae0492.feature`.

## Affected Areas

- [x] Backend (new route + service, constants, schemas)
- [x] Frontend (publish panel, save hook, leave guard, i18n)
- [x] API (new PATCH route, OpenAPI artifact)
- [x] Tests
- Database: no change (columns and the distribution home exist)

## Dependencies

- Blocks: AE-0505, AE-0506.
- Related: ADR-011 (canonical distribution home).

## Progress Log

### 2026-10-22

Ticket written from the dashboard QA triage; failing tests first. Backend route + service, then the
publish panel save, the page wiring and the leave guard; lint fixes (complexity, file size, an import
cycle, a jscpd clone with the blog guard) by extracting helpers, no rule changes.

## Files Touched

- backend/src/rag_backend/api/routes/carousels/copy_edit.py (new), deps.py, router.py
- backend/src/rag_backend/api/schemas/carousel_copy.py (new)
- backend/src/rag_backend/application/services/carousel/carousel_copy_edit_service.py (new)
- backend/src/rag_backend/domain/constants/carousel_copy_edit.py (new)
- backend/tests/integration/test_carousel_copy_edit_ae0492.py, backend/tests/features/carousel_copy_edit_ae0492.feature (new)
- docs/architecture/openapi.json
- frontend/src/modules/publishing/distribution/: components/copy-save-bar.tsx, leave-guard-dialog.tsx,
  publish-panel-parts.tsx (new), publish-panel.tsx, publish-panel-tabs.tsx, types.ts; hooks/use-copy-editor.ts,
  use-leave-guard.ts, use-save-carousel-copy.ts (new), types.ts; lib/copy-editor-state.ts (new); tests
- frontend/src/app/dashboard/create/[id]/publish/page.tsx, use-copy-save.ts (new), tests
- frontend/src/constants/api.ts, frontend/src/modules/publishing/index.ts, i18n en/pt
- frontend/tests/features/publish-copy-save-ae0492.feature (new)

## Test Evidence

Integration tests red first (404 before the route), 14 green after; publish-panel / page / hook Vitest
163 green; backend gate capture green (Postgres gates and mutation in CI); frontend gates green gate by
gate except the main-wide `frontend:security` advisory. Details: `.agent/reports/AE-0492.dev-summary.md`.

## QA Report

External QA: WARN (CI-decided gates only), see `.agent/reports/AE-0492.qa.md`.

## Blockers

None.
