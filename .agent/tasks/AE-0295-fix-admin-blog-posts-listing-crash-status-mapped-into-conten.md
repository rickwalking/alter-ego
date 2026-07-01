# AE-0295 — fix admin blog-posts listing crash: status mapped into content-category badge palette

Status: Review
Tier: T1
Priority: High
Type: Bugfix
Area: frontend
Owner: Unassigned
Branch: TBD
Created: 2026-07-01
Updated: 2026-07-01

## Goal

The dashboard "Posts do Blog" (Blog Posts) listing renders every post card without
crashing, regardless of the post's workflow status.

## Problem

`GET /api/blog-posts` returns posts correctly (verified: envelope `{items, total, limit,
offset}` and every field the adapter reads are present), but the admin listing renders
blank / hits the error boundary in production.

Root cause is a render-time `TypeError`, not a data problem:

1. `frontend/src/modules/editorial-operations/board/blog-posts/adapters/blog-post-adapter.ts:12`
   maps `category: post.status` — it puts the **workflow status** (`"draft"`,
   `"published"`, `"under_review"`, `"approved"`, `"archived"`) into the `category` slot.
2. `frontend/src/app/dashboard/blog-posts/blog-posts-grid.tsx:84-88` renders each regular
   card as `<BlogPostBadge color={post.category.toLowerCase()}>` — so `color` becomes the
   status string.
3. `frontend/src/modules/editorial-operations/board/blog-posts/components/badge.tsx:5` does
   `const { bg, text } = BLOG_POST_BADGE_COLORS[color];` with **no fallback**.
4. `frontend/src/modules/editorial-operations/board/blog-posts/constants.ts:29-44` —
   `BLOG_POST_BADGE_COLORS` is keyed by **content categories / color names** (`security`,
   `ai`, `architecture`, `dev`, `magenta`, `cyan`, `featured`, …). It contains **none** of
   the workflow-status values.

Therefore `BLOG_POST_BADGE_COLORS["draft"]` is `undefined`, and destructuring `undefined`
throws `TypeError: Cannot destructure property 'bg' of undefined` during render of every
non-featured card. The single featured slot (`FeaturedBlogPost`, grid lines 46-48) uses a
hardcoded valid key (`magenta`/`cyan`) so one card can survive while the rest crash — matching
the "not rendering correctly" symptom.

## Scope

- Stop conflating workflow **status** with content **category** in the badge slot. Introduce a
  dedicated status → badge mapping (a `BLOG_POST_STATUS_COLORS` map covering all five statuses:
  `draft`, `under_review`, `approved`, `published`, `archived`) and render the status badge from
  it, OR map `status` to an existing valid palette key.
- Add a safe fallback in `BlogPostBadge` (`badge.tsx`) so an unknown `color` key can never crash
  the listing again (defensive; render a neutral default badge).
- Keep the genuine content-category badge behavior intact for any card that legitimately uses a
  category.

## Non-Goals

- Do not refactor the listing layout or the grid beyond the badge fix.
- Do not add edit/delete/hide controls (that is AE-0296).
- Do not touch the public blog detail route (that is AE-0297).

## Acceptance Criteria

- [ ] The blog-posts listing renders all returned posts with no runtime error for every status
      value (`draft`, `under_review`, `approved`, `published`, `archived`).
- [ ] `BlogPostBadge` renders a defined, non-crashing badge for any unknown/unmapped `color` key
      (safe fallback), proven by a unit test that passes an unmapped key and asserts no throw.
- [ ] A status badge visually distinguishes at least draft vs published (correct label + a
      defined bg/text color).
- [ ] Existing content-category badge usages still render correctly.

## Gherkin Scenarios

```gherkin
Feature: Blog posts admin listing renders for all workflow statuses

  Scenario: Listing renders draft and published posts without crashing
    Given the API returns blog posts with statuses "draft" and "published"
    When the admin opens the "Posts do Blog" dashboard page
    Then every post card is rendered
    And no runtime TypeError is thrown

  Scenario: Badge falls back safely for an unknown color key
    Given a BlogPostBadge is rendered with a color that is not in the palette map
    When the component renders
    Then it renders a neutral default badge
    And it does not throw
```

## Repro Steps

1. Ensure the DB has blog posts in statuses other than the featured/magenta path (e.g. `draft`).
2. Open the dashboard "Posts do Blog" page in production.
3. Observe blank grid / error boundary; console shows `Cannot destructure property 'bg' of undefined`.

## Affected Areas

- [ ] Backend
- [x] Frontend
- [x] Tests

Files:
- `frontend/src/modules/editorial-operations/board/blog-posts/adapters/blog-post-adapter.ts`
- `frontend/src/app/dashboard/blog-posts/blog-posts-grid.tsx`
- `frontend/src/modules/editorial-operations/board/blog-posts/components/badge.tsx`
- `frontend/src/modules/editorial-operations/board/blog-posts/constants.ts`

## Dependencies

- Blocks: AE-0296 (management controls need a non-crashing listing to hang off).
- Related: AE-0297 (public blog route), part of the same production blog-posts troubleshooting sweep.

## Decision Log

### 2026-07-01 — architect + external review (GLM 5.2)

Plan `.agent/reports/AE-0295.arch-plan.md`; review `.agent/reports/AE-0295-0299.skeptical-review.md`
(converged, no blockers). Hardened beyond the raw fix:
- Type `BLOG_POST_STATUS_COLORS` as **`Record<BlogPostStatus, BadgeColor>`** (compile-time
  exhaustiveness) + a keys===enum unit test. `unpublish`→`draft` (verified) means **no 6th status**.
- Type the `BlogPostBadge` status prop as **`BlogPostStatus`** (not `string`) so cross-domain
  confusion (the original root cause) is a compile error, not a runtime fallback.
- Neutral **fallback** for unknown keys (rule-fires regression test: unmapped key → no throw).
- **Cross-layer drift guard:** FE/BE status vocab test or Zod reject-unknown on the API response.
- **Status replaces category** on this surface (category unpopulated today); a category badge is a
  future follow-up with its own responsive test.

## Progress Log

### 2026-07-01

Ticket created from production troubleshooting session. Root cause fully isolated to the
status→category badge mapping crash.

### 2026-07-01 — development (wave AE-0295..0299)

Implemented on `feat/ae-0295-0299-blog-prod-fixes`:
- `BLOG_POST_STATUSES` + `BlogPostStatus` + `toBlogPostStatus` in
  `publishing/blog/constants.ts` (backend enum mirrored; FE/BE contract test).
- `BLOG_POST_STATUS_COLORS: Record<BlogPostStatus, BlogPostBadgeVisual>`
  (compile-time exhaustive) + `BLOG_POST_BADGE_FALLBACK` neutral visual.
- New `BlogPostStatusBadge` typed `BlogPostStatus | null` (null = drifted
  backend value → neutral "Unknown" badge); `BlogPostBadge` gains the safe
  fallback for unmapped keys (rule-fires test).
- Adapter maps status into a dedicated `status` slot; `category` left empty
  (status no longer conflated). Status filter now matches `post.status`;
  filter options i18n-driven from the real 5-status vocabulary (fixes the
  stale `review` option value).

## Files Touched

- `frontend/src/modules/publishing/blog/constants.ts` (new) + `publishing/index.ts`
- `frontend/src/modules/editorial-operations/board/blog-posts/{types,constants,helpers}.ts`
- `frontend/src/modules/editorial-operations/board/blog-posts/components/{badge.tsx,status-badge.tsx,types.ts}`
- `frontend/src/modules/editorial-operations/board/blog-posts/adapters/blog-post-adapter.ts`
- `frontend/src/modules/editorial-operations/index.ts`
- `frontend/src/app/dashboard/blog-posts/{blog-posts-grid.tsx,blog-posts-filters.tsx}`
- `frontend/src/i18n/locales/{en,pt}.json` (`featured`, `status.unknown`)
- `frontend/tests/features/blog-posts-listing-status-badge.feature` (new)
- Tests: `constants.test.ts`, `badge.test.tsx`, `status-badge.test.tsx`,
  `blog-post-adapter.test.ts`, `blog-posts-grid.test.tsx`

## Test Evidence

- `npx vitest run` over the 5 new test files: **18 passed** (badge fallback
  rule-fires, exhaustive status map, draft≠published visuals, adapter
  narrowing, grid renders all 5 statuses + unknown, FE/BE enum contract).
- `npm run typecheck`: clean.
- `bash scripts/ci/gates.sh frontend:lint`: PASS
  (`GATES_JSON: {"pass":1,"fail":0,"skip":0,...}`).

## QA Report

Wave external QA (GLM 5.2, opencode-go, cold context): R1 WARN (0 critical) →
fixes (eac18aee) → R2 confirmation **PASS**. Wave report:
`.agent/reports/AE-0295-0299.qa.md`; pointer: `.agent/reports/AE-0295.qa.md`.

## Blockers

None.
