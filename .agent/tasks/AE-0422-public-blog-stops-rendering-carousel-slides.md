# AE-0422 — Public blog stops rendering carousel slides (A)

Status: Intake
Tier: T1
Priority: P1
Type: Bug
Area: Cross-cutting
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
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

- [ ] AC1: The public blog page renders **no** `<img>` whose `src` contains `/slide-images/`.
- [ ] AC2: `resolveSlideImage` / the positional fallback and the `blog_image_map` read are removed
      from `blog-post-content.tsx`; the component no longer needs `slideImages`.
- [ ] AC3: The carousel design fetch is kept only for theme tokens; a post with no design tokens
      still renders (default theme).
- [ ] AC4: The title renders exactly once (no duplicate H1) — the existing v1 strip may stay until
      AE-0423, but the page has one H1.
- [ ] AC5: `blog_clean_slides.feature` is marked superseded by ADR-0025 (or rewritten to assert no
      carousel slides in blog bodies); the mapping scenarios in `blog_content_cleanup.feature` are
      marked superseded.
- [ ] AC6: A Gherkin scenario documents that the prod hide selects **all** published
      carousel-origin rows — `status == "published"` AND `origin == "carousel"` — with **no**
      body-length or H1-stub filter (all 10 live posts were built by the old pipeline). Hiding uses
      the **unpublish transition semantics** (published → draft, publish stamps cleared, status event
      emitted) and writes a durable marker
      `ai_generation_metadata.hidden_bad_post = {at, reason}` so AE-0426 can select the row after
      its status changed. Hiding is idempotent and never deletes.
- [ ] AC7: Creating/updating a carousel no longer creates, overwrites or publishes a `blog_posts`
      row (`sync_carousel_blog_post` and its calls are gone); a regression test saves a project
      twice and asserts an existing row's content/status are unchanged and no row is created when
      none exists. Deleting a carousel still flips its published blog row to `draft` (orphan
      safety).

## Gherkin Scenarios

- `frontend/tests/features/blog_no_carousel_slides_ae0422.feature` (happy + edge + failure).
- Scenario list: no `/slide-images/` in the rendered body; section without an image renders text
  only; missing design tokens uses the default theme; title rendered once; deprecation note in the
  two retired specs; hide-all-published-carousel-origin criteria + durable marker scenario;
  carousel save does not create/overwrite/publish a blog row.

## Delta

### ADDED

- `blog_no_carousel_slides_ae0422.feature`.
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

## Files Touched

Pending.

## Test Evidence

Pending.

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

## Risk & Size

- **Risk:** Low–Medium — a small backend write-path removal plus a frontend rendering change;
  mitigated by the no-clobber regression test and by shipping before the model migration.
- **Size:** S

## Blockers

None.

## Final Summary

Pending.
