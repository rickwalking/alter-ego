# AE-0411 — Blog dashboard: editor data loss, "New Post" 409 and list fixes

Status: In Development
Tier: T2
Priority: P0
Type: Bug
Area: Cross-cutting
Owner: Claude (owner-requested QA fix)
Agent Lane: developer → qa → release
Branch: fix/ae-0411-blog-dashboard
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

The blog dashboard lists every post with its real live state, "New Post" creates a draft, and the
editor loads and saves posts without losing content.

## Problem

QA run 2026-10-16 (`~/alter-ego-qa/2026-10-16-ui/REPORT.md`):

- **B05 (blocker)** The editor looked the post up in the **list** response (summaries have no
  `content`, first page only), read only `content.body` (carousel rows store `content.markdown`)
  and always sent `content: {body}`. Saving a title change wiped the stored markdown.
- **B06 (blocker)** `BlogPostModel.from_entity` defaults `slug` to `""` and `slug` is unique, so
  every create after the first slug-less post was a 409. The UI swallowed the error.
- **B07 (major)** The adapter set `featured = status === "published"`; the page rendered
  `find(featured)` once plus `filter(!featured)`, so only one published post showed.
- **B17 (major)** The carousel dual-write stores carousel posts as `published`; the public read
  also needs the carousel `is_public`. The dashboard showed "Publicado · Destaque" for posts whose
  carousel was still in review.
- **B19 (minor)** Editor save errors (422) were swallowed; inputs had no label/required/maxLength.
- **B20 (minor)** Hardcoded "24 posts"; a category filter with no backend category always emptied
  the list; no empty state.
- **B24 (part)** Hardcoded English strings on the blog-posts dashboard.

## Scope

- Backend: generate a unique slug when none is given; map a slug clash to a clear 409; expose
  `is_public` on list summaries (same rule as the public API); validate excerpt length (500).
- Frontend: editor loads the detail endpoint, handles both content shapes, sends only changed
  fields and keeps other content keys; client validation + visible server errors; list renders
  all posts with at most one featured (live) card; not-live badge; real counter; empty states;
  category filter removed; i18n en/pt.

## Non-Goals

- Changing the carousel dual-write status or the public visibility rule.
- Re-translating carousel blog translations when the PT markdown is edited in the editor.
- Server-side pagination UI for more than 100 posts.

## Acceptance Criteria

- [x] Opening any post (also beyond the first list page) loads it via `GET /api/blog-posts/{id}`.
- [x] The body shows `content.body`, or `content.markdown` for carousel posts.
- [x] A title-only save sends only `title`; a body edit keeps every other content key.
- [x] "New Post" creates a draft (generated slug `untitled-draft-xxxxxxxx`); a failed create shows
      an error; a duplicate given slug is a 409 `blog_post_slug_conflict`.
- [x] All posts render; at most one featured card, and only a live post can be featured.
- [x] A `published` post that is not public shows "Awaiting carousel release", no Hide action.
- [x] Counter shows the real count; no category filter; empty / no-results states.
- [x] Editor: labelled inputs, `required`, `maxLength` 255/500, inline errors, save errors shown,
      no navigation on failure, no unhandled rejections.
- [x] Blog-posts dashboard strings come from en/pt messages.

## Gherkin Scenarios

- `backend/tests/features/blog_dashboard_ae0411.feature`
- `frontend/tests/features/blog-dashboard-ae0411.feature`

## Delta

### ADDED

- `backend/src/rag_backend/modules/publishing/domain/blog_slug.py` (slug generation).
- `public_blog_post_ids` (public_visibility.py) + `BlogPostCrudPort.public_post_ids`.
- `BlogPostSummaryResponse.is_public`; `ERR_BLOG_POST_SLUG_CONFLICT`; `BLOG_EXCERPT_MAX_LENGTH`.
- Frontend `editor-content.ts`, `blog-post-requests.ts`, `blog-post-edit-fields.tsx`,
  `BlogPostsList`, i18n keys.

### MODIFIED

- `create_blog_post` route (slug clash → 409), `list_blog_posts` (adds `is_public`).
- `useBlogPostEditor` (detail query, partial update, validation, typed save errors).
- Dashboard list page, filters, grid, card actions, status badge, adapter.

### REMOVED

- Category filter + `BLOG_POST_CATEGORY_OPTIONS`; `DashboardBlogPost.category` / `featured`.
- `RichTextEditor` use in the blog editor (it reformatted stored markdown); the body is a textarea.

## Affected Areas

- Backend: blog_post routes/schemas, publishing module (domain, ports, ACL, visibility)
- Frontend: dashboard/blog-posts, modules/publishing/blog, editorial-operations board blog-posts
- Database: none (no migration)
- API: `GET /api/blog-posts` items gain `is_public`; create 409 detail; excerpt max 500 (422)
- Tests: backend unit + integration, frontend vitest
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0296, AE-0347, AE-0295

## Implementation Plan

1. Gherkin features (backend + frontend).
2. Backend slug generation, 409 mapping, `is_public` on list.
3. Frontend editor (detail query, content shapes, partial update, validation, errors).
4. Frontend list (all posts, single live featured, not-live badge, counter, empty states, i18n).
5. Gates: `scripts/ci/gates.sh backend` and `frontend`.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17 10:00

Ticket created; implementation, tests and gates run in branch `fix/ae-0411-blog-dashboard`.

## Files Touched

See the PR diff.

## Test Evidence

See the PR body (gate runs).

## QA Report

Pending.

## Decision Log

- **B17: expose live state instead of changing the dual-write status.** The carousel release
  (`LegacyPublishingAcl.release_carousel`) only sets the carousel `is_public`; it never touches
  the blog row. Writing carousel blog rows as `draft` would therefore keep them hidden after the
  release (and the AE-0347 visibility rule already blocks unreleased ones). The safest fix keeps
  the stored status and the public rule unchanged and has the list report `is_public` using the
  SAME clause as the public API; the UI shows "Awaiting carousel release" for `published` but
  not public posts, never features them, and hides "Hide (revert to draft)" for them (hiding
  would keep the post hidden after the carousel release).
- **B07: featured = newest live post** (single), every other post as a regular card.
- **B20: category filter removed** — the backend has no category field.
- **B05: body edited as source text.** The TipTap `RichTextEditor` parsed markdown as HTML and
  `setContent` (TipTap v3, `emitUpdate` defaults to true) pushed the flattened text back, which
  would rewrite the body on load. A textarea round-trips the stored text exactly.

## Blockers

None.

## Final Summary

Pending.
