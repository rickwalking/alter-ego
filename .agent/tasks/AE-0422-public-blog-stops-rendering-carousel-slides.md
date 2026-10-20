# AE-0422 — Public blog stops rendering carousel slides (A)

Status: Done
Tier: T1
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0422-blog-no-carousel-slides
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-18

## Goal

Make the public blog body stop injecting rendered carousel slides, ship this first and alone, retire
the stale slide specs, hide **every** already-published carousel-origin post (all were built by the
old pipeline), and stop the carousel write path from auto-publishing blog posts. This is the
immediate half of ADR-0025: a blog
post must no longer display Instagram cards with baked-in text (QA F-01, F-07) and a carousel save
must never create/overwrite/publish a blog post, even before the structured document model
(AE-0423) lands.

## Problem

`frontend/src/modules/publishing/blog/components/public-post/blog-post-content.tsx:175-238` injects a
carousel slide image under each H2 section, sourced from the carousel design's
`images.slides` (`/api/carousels/{id}/design`), which `design_token_utils.py:216-221,280,308-313`
forces to the **rendered** slides (`/slide-images/pt/slide_N.jpg`). Those images are Instagram cards
with the heading/body text baked in (F-01), carry empty `alt=""` (`:186`, F-07), and are mapped to
sections positionally because `blog_image_map` is `null` (F-07 wrong-section risk). The spec
`blog_clean_slides.feature` promises raw art is used and renders the opposite.

## Scope

- Frontend: stop reading carousel design for blog body images; render sections without the injected
  slide image (the structured per-section images arrive in AE-0423). Keep the carousel design fetch
  only for theme (colors/typography) on carousel-origin posts.
- Backend **write path**: remove the `sync_carousel_blog_post` upsert and its calls in
  `carousel_repository.py` (`create_project` / `update_project`). It writes
  `blog_posts.content = {markdown, translations}` **and sets `status='published'`** on every carousel
  save, which re-publishes hidden/soon-to-be-hidden bad posts and would clobber a v2 document. After
  this ticket a blog row is created only by `POST /blog-posts/from-carousel` / `generate` (always
  `draft`). **Keep `detach_carousel_blog_posts` on delete** (it flips a published carousel blog row
  to `draft` before the FK `SET NULL`, preventing a publicly-visible orphan); fold it into the
  repository and delete the rest of the module if that is cleaner. Update the tests that assert the
  carousel auto-creates a blog row (workflow tests must create their row explicitly).
- Retire/rewrite the stale specs in place: `frontend/tests/features/blog_clean_slides.feature` and
  the positional slide-image mapping scenarios in
  `frontend/tests/features/blog_content_cleanup.feature` (deprecate with a pointer to ADR-0025;
  do not silently delete).
- Add the hide-all **selection criteria** as a documented, testable spec (a Gherkin scenario
  and a short section here); the prod action itself is the orchestrator's (owner approval), not this
  ticket's.

## Non-Goals

- The structured document model, migration and per-section images (AE-0423).
- The editor (AE-0424) and generation (AE-0425).
- Running the actual unpublish/hide of prod rows (orchestrator action).
- Removing the `blog_image_map` **field** from the carousel domain/schema/design payload and deleting
  the dead blog-v1 files (AE-0428). This ticket only stops reading it.

## Acceptance Criteria

- [x] AC1: The public blog page renders **no** `<img>` whose `src` contains `/slide-images/`.
- [x] AC2: `resolveSlideImage` / the positional fallback and the `blog_image_map` read are removed
      from `blog-post-content.tsx`; the component no longer needs `slideImages`.
- [x] AC3: The carousel design fetch is kept only for theme tokens; a post with no design tokens
      still renders (default theme).
- [x] AC4: The title renders exactly once (no duplicate H1) — the existing v1 strip may stay until
      AE-0423, but the page has one H1.
- [x] AC5: `blog_clean_slides.feature` is marked superseded by ADR-0025 (or rewritten to assert no
      carousel slides in blog bodies); the mapping scenarios in `blog_content_cleanup.feature` are
      marked superseded.
- [x] AC6: A Gherkin scenario documents that the prod hide selects **all** published
      carousel-origin rows — `status == "published"` AND `origin == "carousel"` — with **no**
      body-length or H1-stub filter (all 10 live posts were built by the old pipeline). Hiding uses
      the **unpublish transition semantics** (published → draft, publish stamps cleared, status event
      emitted) and writes a durable marker
      `ai_generation_metadata.hidden_bad_post = {at, reason}` so AE-0426 can select the row after
      its status changed. Hiding is idempotent and never deletes.
      Implemented (testable spec + operator action):
      `backend/src/rag_backend/infrastructure/database/blog_post_hide.py` (`is_hide_target` predicate
      + `BlogPostHideService.hide`, dry-run `preview`), operator CLI
      `backend/scripts/hide_bad_carousel_posts.py` (`--dry-run` default, `--apply`), tests
      `backend/tests/unit/infrastructure/test_blog_post_hide.py`.
- [x] AC7: Creating/updating a carousel no longer creates, overwrites or publishes a `blog_posts`
      row (`sync_carousel_blog_post` and its calls are gone); a regression test saves a project
      twice and asserts an existing row's content/status are unchanged and no row is created when
      none exists. Deleting a carousel still flips its published blog row to `draft` (orphan
      safety).
- [x] AC8: The legacy public read (`GET /api/carousels/{project_id}/blog` and `/blog/{lang}`) is
      gated on the canonical `origin='carousel'` `blog_posts` row's `status`: anonymous callers get
      a uniform 404 (ADR-0013) unless the row is `published`, so a hidden post stops being served at
      `/blog/<carousel project id>` even though `carousel_projects.is_public` is still true.
      Authenticated dashboard/editor preview keeps reading regardless.

## Gherkin Scenarios

- `frontend/tests/features/blog_no_carousel_slides_ae0422.feature` (happy + edge + failure).
- Scenario list: no `/slide-images/` in the rendered body; section without an image renders text
  only; missing design tokens uses the default theme; title rendered once; deprecation note in the
  two retired specs; hide-all-published-carousel-origin criteria + durable marker scenario;
  carousel save does not create/overwrite/publish a blog row.

## Delta

### ADDED

- `blog_no_carousel_slides_ae0422.feature`.
- `themeOnlyDesign()` in `frontend/src/lib/public-blog.ts`.
- `backend/src/rag_backend/infrastructure/database/blog_post_hide.py` + `BlogPostHideService`,
  `is_hide_target`, `HideRun`/`HideReport` (AC6).
- `backend/scripts/hide_bad_carousel_posts.py` (AC6 operator CLI, dry-run default).
- `backend/tests/unit/infrastructure/test_carousel_save_blog_noop.py` (AC7 regression) and
  `test_blog_post_hide.py` (AC6).
- A short "hide-all selection criteria" section in this ticket (used by AE-0426).

### MODIFIED

- `blog-post-content.tsx` (drop slide image injection), its types, and any prop plumbing in
  `frontend/src/app/(public)/blog/[id]/page.tsx`.
- `blog_clean_slides.feature`, `blog_content_cleanup.feature` (deprecation banner).

### REMOVED

- `resolveSlideImage`, `ResolveSlideImageOptions`, the positional fallback, `slideImageUrls`.
- `sync_carousel_blog_post` and its two call sites in `carousel_repository.py`
  (`detach_carousel_blog_posts` stays; the v2 document becomes the sole content writer in AE-0423).

## Affected Areas

- Backend: carousel repository write path (upsert removed; delete-detach retained)
- Frontend: public blog rendering, tests
- Database: none (no schema change; rows are no longer auto-created on carousel save)
- API: none (the blog read endpoint is unchanged)
- Tests: frontend unit + feature specs; backend no-clobber regression test
- Docs: ADR-0025, this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: normal (backend + frontend; safe to ship alone)

## Hide-all selection criteria (spec only; prod action is the orchestrator's)

Select a `blog_posts` row to hide when **both** hold:

- `status == "published"`, **and**
- `origin == "carousel"`.

There is **no** body-length or H1-stub filter: every currently published post (10 at the time of
the sweep) was
built by the old pipeline (screenshots with baked-in text), so all of them are hidden and rebuilt
through the new writer (AE-0426). Standalone/non-carousel rows and rows already in `draft` are not
selected.

Hide = run the existing **unpublish** transition (published → draft, clear publish stamps, emit the
status event; public uniform 404 per ADR-0013) **and** write the durable marker
`ai_generation_metadata.hidden_bad_post = {at, reason}`. The marker is what AE-0426 selects; a plain
`status = draft` update is not enough because AE-0426 cannot distinguish a hidden bad post from an
ordinary draft. **No deletion.** Hiding twice is a no-op (same marker, same status).

Implemented in `backend/src/rag_backend/infrastructure/database/blog_post_hide.py`:

- `is_hide_target(post)` — the selection predicate (origin carousel AND status published).
- `BlogPostHideService.preview(db)` — dry-run: ids that `hide` would change, no writes.
- `BlogPostHideService.hide(db, HideRun(reason, now, user_id))` — per selected row: status → `draft`,
  `published_at`/`submitted_for_review_at` cleared, `lock_version` bumped, marker written, and
  `EVENT_TYPE_BLOGPOST_STATUS_CHANGED` emitted with the old/new status (transactional outbox, same as
  the workflow routes). The caller owns the commit; a second run selects nothing.
- `backend/scripts/hide_bad_carousel_posts.py` — operator CLI (`--dry-run` is the default, `--apply`
  writes).

It mirrors the unpublish field write directly rather than calling `BlogVisibilityPort` so the
operator path adds no new `application -> infrastructure` (AE-0082 baseline) edge; the semantics
(which fields clear, which event fires) match the workflow unpublish route byte-for-byte. Running it
against production is still the orchestrator's owner-approved action, not part of this ticket.

### Legacy public-URL gate (AC8)

Hiding a row flips its `status` to `draft`, but the legacy carousel-blog URL is keyed by the
**carousel project id** and was previously gated only on `carousel_projects.is_public` — which the
hide action does not change — so a hidden post stayed reachable at `/blog/<carousel project id>`
through `GET /api/carousels/{project_id}/blog` (row read) and `/blog/{lang}` (embedded read). Both
routes now call `_assert_blog_visible` (`media.py`): for anonymous callers they 404 (uniform,
ADR-0013) unless `PublishingReadAcl.is_carousel_blog_published(project_id)` finds a `published`
`origin='carousel'` row; an authenticated caller (owner/admin preview) bypasses the gate. The
predicate is exposed on the publishing read port/adapters so the route adds no new infra import.

## Dependencies

- Blocks: none (ships first).
- Blocked by: none.
- Related: AE-0423, AE-0424, AE-0425, AE-0426, AE-0428, ADR-0025, ADR-0013.

## Implementation Plan

1. Write `blog_no_carousel_slides_ae0422.feature`.
2. Remove slide-image injection from the public renderer; keep theme-only design fetch.
3. Remove `sync_carousel_blog_post` and its calls; keep the delete-time detach; add the no-clobber
   regression test.
4. Add the deprecation banners to the two stale specs.
5. Frontend unit tests + backend test; `bash scripts/ci/gates.sh frontend` and `backend`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked (no dead `slideImages` prop)

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave A).
Updated after the owner revision: also removes the carousel→blog dual-write (it re-published blog
posts on every carousel save and would clobber v2).

### 2026-10-18 (dev)

Implemented A end-to-end on `feat/ae-0422-blog-no-carousel-slides`.

Frontend (commit `54cfcafad`): `blog-post-content.tsx` no longer reads any carousel design image;
the section renderer emits `ReactMarkdown` only. Removed `resolveSlideImage`, the positional
`slideImage` fallback, `ResolveSlideImageOptions`, `slideImages`, and the now-unused
`CAROUSEL_SLIDE_WIDTH/HEIGHT` constants; dropped the removed symbols from the publishing barrel. New
`themeOnlyDesign()` in `lib/public-blog.ts` keeps the theme tokens but strips `images`
(`hero`/`slides`/`rendered_slides_pt`/`rendered_slides_en`/`blog_image_map`), so no carousel image
URL can reach the page.

Backend (commits `a50396da7`, `17844e12c`, `8f8a45363`): removed `sync_carousel_blog_post` and its
`create_project`/`update_project` calls; deleted `carousel_blog_dual_write.py` and folded the
delete-time `_detach_carousel_blog_posts` into `carousel_repository.py`; added the AC6 hide service +
CLI. Tests were updated to seed the carousel-origin blog row explicitly instead of relying on the
removed auto-create.

## Files Touched

Frontend:

- `frontend/src/modules/publishing/blog/components/public-post/blog-post-content.tsx` (+ `.test.tsx`)
- `frontend/src/modules/publishing/blog/components/public-post/types.ts`
- `frontend/src/app/(public)/blog/[id]/page.tsx`
- `frontend/src/lib/public-blog.ts` (+ `.test.ts`)
- `frontend/src/constants/blog.ts`
- `frontend/src/modules/publishing/index.ts`
- `frontend/tests/features/blog_no_carousel_slides_ae0422.feature` (new)
- `frontend/tests/features/blog_clean_slides.feature`, `blog_content_cleanup.feature`,
  `public-blog-polish-ae0412.feature` (superseded/rewritten scenarios)

Backend:

- `backend/src/rag_backend/infrastructure/database/carousel_repository.py` (upsert removed; detach inlined)
- `backend/src/rag_backend/infrastructure/database/distribution_home.py` (docstrings)
- `backend/src/rag_backend/infrastructure/database/blog_post_hide.py` (new, AC6)
- `backend/src/rag_backend/infrastructure/database/carousel_blog_dual_write.py` (deleted)
- `backend/scripts/hide_bad_carousel_posts.py` (new, AC6 CLI)
- `backend/tests/features/blog_no_carousel_slides_ae0422.feature` (new)
- `backend/tests/unit/infrastructure/test_carousel_repository_detach.py`
- `backend/tests/unit/infrastructure/test_carousel_save_blog_noop.py` (new)
- `backend/tests/unit/infrastructure/test_blog_post_hide.py` (new)
- `backend/tests/integration/test_publishing_safety_net.py`, `test_presentation_safety_net.py`
  (seed the carousel-origin blog row explicitly)
- `backend/src/rag_backend/api/routes/carousels/media.py` (AC8: `_assert_blog_visible` on both blog reads)
- `backend/src/rag_backend/modules/publishing/{application/service.py,domain/ports.py,infrastructure/publishing_port_adapters.py,infrastructure/publishing_read_acl.py}`
  (AC8: `carousel_blog_is_published` / `is_carousel_blog_published`)
- `backend/tests/integration/carousel_consolidation/helpers.py` (`seed_carousel_blog_row`),
  `.../test_legacy_visibility.py` (published-row readable; public carousel + draft row 404;
  carousel publish does not publish the blog)

Note: the branch also carries the plan artifacts added by the architecture commit (ADR-0025, the
blog-post-document-model doc, the AE-0423..AE-0428 tickets/feature files) — not part of this
implementation.

## Test Evidence

- Frontend: `npm run test -- --run` → 1529 passed (181 files). `npm run typecheck` clean. `npm run
  build` succeeds. `bash scripts/ci/gates.sh frontend --changed-only` → 13 PASS / 0 FAIL.
- Backend: `uv run pytest tests/unit -q` → 4710 passed, 1 skipped. `uv run pytest tests/integration
  -q` → 700 passed, 13 skipped. `bash scripts/ci/gates.sh backend --changed-only` → 17 PASS / 0 FAIL
  (format, lint, strict-diff, type, imports, arch-ratchet, docstrings, dead-code, …).
- New AC6 tests: `backend/tests/unit/infrastructure/test_blog_post_hide.py` (hides, idempotent
  re-run, standalone untouched, draft untouched, marker preserves metadata, dry-run writes nothing,
  real status event via `WorkflowEventService`).
- New AC7 tests: `test_carousel_save_blog_noop.py` (no row created on save; existing row's
  content/status unchanged; hidden post not re-published; ADR-0011 distribution mirror still written)
  and the rewritten `test_carousel_repository_detach.py`.
- New AC8 tests: `tests/unit/modules/publishing/test_publishing_read_projection.py::test_public_visibility_gate`
  (absent/draft → False, published → True) and `tests/integration/test_presentation_safety_net.py`
  (hidden draft 404 for anonymous on both routes; published 200; authenticated preview 200) plus
  `tests/integration/carousel_consolidation/test_legacy_visibility.py`
  (`test_public_blog_when_row_published`, `test_public_carousel_with_draft_row_is_hidden`,
  `test_explicit_publish_sets_is_public` now asserts the carousel-publish/blog-publish separation).
  Gherkin: `backend/tests/features/blog_no_carousel_slides_ae0422.feature` (four public-visibility
  scenarios).
- CI (PR #144): all 33 checks green, including `backend / Test & Coverage`, `backend / Mutation`
  (blocking ≥75%) and `frontend` gates; `mergeStateStatus: CLEAN`.

## QA Report

Pending.

## Decision Log

- **Hide all old-pipeline posts, not just thin ones.** Every published carousel-origin post was
  assembled by the old pipeline and shows the same defects (baked-in slide text, positional images,
  empty alt). Filtering by length/H1 would leave some of them live, so the owner chose an
  origin+status sweep; AE-0426 rebuilds them all as drafts.
- **Remove now, model later.** The owner's most visible complaint (slides with baked-in text) is
  independent of the new model; deferring it until AE-0423 keeps screenshot slides live longer. So A
  removes the injection first, accepting that body images are absent until B/C/D add their own.
- **Keep the design fetch for theme.** Carousel-origin posts still need color/typography tokens;
  only the image path is removed. A standalone post with no tokens uses the default theme.
- **Deprecate, don't delete specs.** AE-0180/CLAUDE.md require retiring a spec visibly; the two specs
  encode the old contract and are marked superseded by ADR-0025.
- **Kill the upsert here, not in the cleanup wave.** `sync_carousel_blog_post` writes v1 markdown
  and `status='published'` on every carousel save. Left in place, it would undo the hide action
  (AE-0426) and, after v2, clobber an owner-edited document; removing it in the first ticket makes
  "carousel-origin posts are always drafts" true before anything else ships.
- **Keep the delete-time detach.** `detach_carousel_blog_posts` is a different concern: the FK is
  `ON DELETE SET NULL`, so without the published→draft flip a deleted carousel leaves a detached but
  publicly visible post. It stays (inlined or kept in the module); AE-0428 does not touch it.
  **Known behavior (not changed here):** deleting a carousel also unpublishes an already-published
  v2 post (published → draft). That is the safe default for v1 orphans; keeping a v2 post live after
  its source carousel is deleted is a possible follow-up, not part of this epic.
- **Strip the carousel design image entirely, including `images.hero`.** AC1 forbids any `<img>` src
  containing `/slide-images/`, and the design's `images.hero` **is** a rendered slide
  (`design_token_utils.py::_public_rendered_slide_urls` / `_build_default_design_tokens` build it as
  `/api/carousels/{id}/slide-images/pt/slide_1.jpg`). So the public page must show no carousel design
  image at all — `themeOnlyDesign()` keeps colors/typography and drops `images`. A standalone post
  still shows its own `featured_image_url`.
- **Preserve the ADR-0011 distribution mirror.** Removing `sync_carousel_blog_post` also removed the
  only writer of `blog_posts.distribution`. Rather than drop that behavior, `create_project` /
  `update_project` now call the existing `write_distribution` (no-op when there is no row; never
  touches `content`/`status`). This keeps the "distribution home" contract live while satisfying "no
  row created/published/overwritten".
- **Put the AC6 hide service in `infrastructure/database`, not `application`.** It writes
  `BlogPostModel` directly and reuses `WorkflowEventService`, so an `application` home would add a
  new `application -> infrastructure` edge to the generated AE-0082 baseline. Placing it next to
  `workflow_timeout_repository` (which already does infra→application) keeps `.importlinter`
  untouched.
- **Seed the carousel-origin blog row explicitly in the safety-net tests.** Those tests exercised the
  removed auto-create path; making them insert the AE-0127-shape row directly keeps them testing the
  *read* path (which this ticket does not change) rather than deleting their coverage.

## Risk & Size

- **Risk:** Low–Medium — a small backend write-path removal plus a frontend rendering change;
  mitigated by the no-clobber regression test and by shipping before the model migration.
- **Size:** S

### 2026-10-19 (takeover)

Finished AC8: the legacy carousel-blog read now 404s for anonymous callers when the canonical
`origin='carousel'` row is not `published`; authenticated preview is unaffected. Added the
public-visibility predicate to the publishing read port/ACL, Gherkin + unit + integration coverage,
and updated the two `test_legacy_visibility.py` scenarios that relied on the superseded
`is_public`-only contract (per ADR-0025: a carousel going public never publishes its blog post).
PR #144 CI green (33/33).

## Blockers

None.

## Final Summary

Implemented and pushed on `feat/ae-0422-blog-no-carousel-slides` (commits `54cfcafad`, `a50396da7`,
`17844e12c`, `8f8a45363`). The public blog body renders text only (no carousel design image reaches
the page), the carousel write path no longer creates/overwrites/publishes blog rows (delete-time
detach retained), and the AC6 hide action ships as a tested service + dry-run-default CLI. All seven
acceptance criteria are met; every local gate is green. Production hiding is the orchestrator's
owner-approved action.

**Merged and closed (orchestrator, 2026-10-20).** Merged via #144 into the plan branch, shipped to main with #143 (6336338, 2026-10-19). Prod: hide script applied (27 published carousel posts -> draft + hidden_bad_post); public list 0 until rebuilt drafts are republished.
