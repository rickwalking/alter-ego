# AE-0296 — blog post management: edit, delete, and hide controls in dashboard

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: fullstack
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

An admin can edit, delete, and hide (unpublish) an existing blog post directly from the
dashboard "Posts do Blog" listing.

## Problem

There is no UI to manage existing blog posts. Investigation confirms the gap is **frontend-only** —
the backend already exposes all three actions:

- Edit: `PUT /blog-posts/{post_id}` — `backend/src/rag_backend/api/routes/blog_post.py:175`
  (optimistic-lock via `If-Match`).
- Delete: `DELETE /blog-posts/{post_id}` — `backend/src/rag_backend/api/routes/blog_post.py:236`
  (204).
- Hide: `POST /blog-posts/{post_id}/unpublish` —
  `backend/src/rag_backend/api/routes/blog_post_workflow.py:329` (published → prior status). The
  `status` column (`backend/.../models/blog_post.py:47`, indexed) supports the transition.

Frontend gaps:
- `frontend/src/modules/publishing/blog/hooks/use-blog-posts.ts` has `updatePost` (67) and
  `deletePost` (86) but **no `unpublish`** function; the returned `delete` (143) is dead code
  (no caller).
- `frontend/src/app/dashboard/blog-posts/page.tsx` only uses `create`. Cards in
  `blog-posts-grid.tsx` have **no `Link`/`href`/`onClick`** — they look clickable but navigate
  nowhere, so there's no entry point to any management action.
- The edit page `frontend/src/app/dashboard/blog-posts/[id]/edit/page.tsx` exists and works, but is
  reachable **only** programmatically right after create (`use-new-blog-post.ts:33`). It offers only
  "Save Changes" / "Back to List" — no Delete, no Hide.
- The public admin panel `blog-post-admin-panel.tsx:80` has a Delete button, but it calls
  `useDeleteCarousel` (deletes the underlying carousel), **not** the blog-post DELETE endpoint.
- Orphan i18n key `dashboard.blogPosts.confirmDelete` (`en.json:749`) is unused — a planned-but-never-wired
  delete UI.

## Scope

- Make listing cards actionable: add an Edit affordance that navigates to the existing edit page
  (`BLOG_POST_EDIT` route), reachable for any post in the listing.
- Add a Delete action wired to the existing `deletePost` hook (`DELETE /blog-posts/{id}`), with a
  confirmation dialog (reuse the orphaned `confirmDelete` i18n key).
- Add a Hide/Unhide (unpublish) action: add an `unpublish` function to `use-blog-posts.ts` calling
  `POST /blog-posts/{id}/unpublish`, and surface a Hide control for published posts (and reflect the
  resulting status in the badge from AE-0295).
- Invalidate/refetch the listing query after each mutation so the grid reflects the change.
- Add the missing i18n strings (en + pt) for edit/delete/hide labels + confirm copy.

## Non-Goals

- No backend changes — all endpoints already exist.
- Do not build a new blog editor; reuse the existing edit page.
- Do not change the "delete carousel" behavior of the public admin panel (out of scope; note it
  targets a different resource).
- The badge/status rendering crash itself is fixed in AE-0295, not here.

## Acceptance Criteria

- [ ] Each post card in the dashboard listing exposes Edit, Delete, and Hide/Unhide actions
      (Hide shown for published posts, Unhide/restore for hidden ones).
- [ ] Edit navigates to the existing edit page for the selected post; saving persists via
      `PUT /blog-posts/{id}` and returns to the listing.
- [ ] Delete calls `DELETE /blog-posts/{id}` after an explicit confirmation; on success the post
      is removed from the listing (query invalidated/refetched).
- [ ] Hide calls `POST /blog-posts/{id}/unpublish`; the card's status badge updates to the
      post-unpublish status without a full reload.
- [ ] `use-blog-posts.ts` exposes a real `unpublish` function; the previously dead `delete` path is
      either wired to a control or removed.
- [ ] All new user-facing strings exist in both `en.json` and `pt.json` (no hardcoded copy).

## Gherkin Scenarios

```gherkin
Feature: Manage blog posts from the dashboard

  Scenario: Edit an existing post
    Given a blog post exists in the listing
    When the admin clicks Edit on its card
    Then the edit page opens for that post
    And saving changes persists via PUT and returns to the listing

  Scenario: Delete a post with confirmation
    Given a blog post exists in the listing
    When the admin clicks Delete and confirms
    Then DELETE /blog-posts/{id} is called
    And the post disappears from the listing

  Scenario: Hide a published post
    Given a published blog post exists in the listing
    When the admin clicks Hide
    Then POST /blog-posts/{id}/unpublish is called
    And the card's status badge updates to the unpublished status

  Scenario: Cancelling delete keeps the post
    Given the delete confirmation dialog is open
    When the admin cancels
    Then no DELETE request is sent
    And the post remains in the listing
```

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

Files:
- `frontend/src/modules/publishing/blog/hooks/use-blog-posts.ts`
- `frontend/src/app/dashboard/blog-posts/page.tsx`
- `frontend/src/app/dashboard/blog-posts/blog-posts-grid.tsx`
- `frontend/src/app/dashboard/blog-posts/[id]/edit/page.tsx`
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt.json`

## Dependencies

- Blocked by: AE-0295 (listing must render without crashing before controls are usable).
- Related: AE-0297 (public visibility of hidden posts).

## Decision Log

### 2026-07-01 — architect + external review (GLM 5.2)

Plan `.agent/reports/AE-0296.arch-plan.md`; review `.agent/reports/AE-0295-0299.skeptical-review.md`
(converged, no blockers). Now **fullstack** (was frontend) — a small backend guard is required:
- **Hide = unpublish → fixed `draft`** (verified `legacy_publishing_acl.py:124-134`); reuses the
  existing 5-status set (no new status). Not a symmetric toggle — restore = normal publish workflow.
- **DELETE 409 guard (backend):** allowlist over the complete `BlogPostOrigin{standalone,carousel}`;
  hard delete only for `standalone`; `carousel`-origin ⇒ 409 (deleting it 404s the public carousel
  blog). FE offers Hide/Archive for carousel-origin.
- **Erasure lifecycle** (compliance): carousel-origin erasure = deleting the parent carousel
  project, which **flips the orphan blog row to `draft`** (must land before/with the 409 guard).
- **If-Match on all three mutations** (PUT already; add DELETE + unpublish) with 412 handling.

## Progress Log

### 2026-07-01

Ticket created from production troubleshooting session. Backend endpoints confirmed; scope now FE
wiring + a small backend delete-integrity guard + unpublish If-Match (see Decision Log).

### 2026-07-01 — development (wave AE-0295..0299)

Backend:
- DELETE `/blog-posts/{id}`: requires `If-Match` (428 when absent, 409
  `version_conflict` when stale) + origin guard — carousel-origin rows still
  linked to a project ⇒ 409 `carousel_origin_delete_blocked`; detached rows
  (project_id NULL) are hard-deletable. Policy sets
  (`BLOG_POST_HARD_DELETABLE_ORIGINS` / `BLOG_POST_LINK_GUARDED_ORIGINS`) with
  a completeness test over every `BlogPostOrigin` member.
- POST `/unpublish`: requires `If-Match` (428/409), bumps `lock_version` on the flip.
- `delete_project` (carousel repo) now calls `detach_carousel_blog_posts`
  (dual-write module): published carousel-origin rows revert to draft (stamps
  cleared, lock bumped) in the same transaction — no orphaned public rows.
- `origin` (+ `project_id` on summaries) exposed in blog-post responses.

Frontend:
- `use-blog-posts`: `delete`/`unpublish` send `If-Match`; 409s map to typed
  `BlogPostMutationError` (carousel guard vs version conflict, which refetches);
  dead `delete` path wired.
- Cards get Edit (link), Hide (published only, "revert to draft" copy), Delete
  (standalone only, `NeonModal` confirmation via `useBlogPostActions`); errors
  surface as localized copy. Edit page save returns to the listing.
- i18n: `actions.hide`, `errors.*` (en+pt).

Deviation: no symmetric "Unhide" control (per Decision Log — restore is the
normal publish workflow, not a one-click toggle). Note: version-conflict is
surfaced as **409 `version_conflict`** (matching the PUT convention), not 412.

## Files Touched

Backend:
- `src/rag_backend/domain/constants/blog_post.py` (delete policy + error)
- `src/rag_backend/api/routes/blog_post.py` (DELETE guard + If-Match)
- `src/rag_backend/api/routes/blog_post_workflow.py` (unpublish If-Match)
- `src/rag_backend/api/schemas/blog_post.py` (origin echo)
- `src/rag_backend/infrastructure/database/{carousel_blog_dual_write,carousel_repository}.py`
- Tests: `tests/unit/domain/test_blog_post_delete_policy.py`,
  `tests/unit/infrastructure/test_carousel_repository_detach.py`,
  `tests/integration/test_blog_post_management_ae0296.py`,
  `tests/features/blog_post_management_ae0296.feature`

Frontend:
- `src/modules/publishing/blog/{constants,types}.ts`, `publishing/index.ts`
- `src/modules/publishing/blog/hooks/use-blog-posts.ts` (+ test)
- `src/modules/editorial-operations/board/blog-posts/{types.ts,adapters/blog-post-adapter.ts}`
- `src/app/dashboard/blog-posts/{page.tsx,types.ts,blog-posts-grid.tsx,blog-posts-actions.tsx,use-blog-post-actions.ts}` (+ tests)
- `src/app/dashboard/blog-posts/[id]/edit/page.tsx`
- `src/i18n/locales/{en,pt}.json`
- `tests/features/blog-posts-management.feature`

## Test Evidence

- Backend: `uv run pytest` over the 3 new test files — **14 passed** (428/409
  guards, origin policy completeness, detach flip, origin echo).
- Backend `ruff check` + `mypy --explicit-package-bases`: clean (533 files).
- Frontend: `npx vitest run` over blog-posts scope — **29 passed** (If-Match
  transport, typed 409 mapping, hide/delete visibility rules, confirm/cancel,
  version-conflict copy).
- `bash scripts/ci/gates.sh frontend:lint`: PASS.

## QA Report

Pending.

## Blockers

None.
